// Package harness 是 Agent Harness：围绕无状态 ReAct Agent 的确定性运行时外壳。
//
// 职责边界（Agent 本身只负责推理与工具调用）：
//   - 会话锁：同一会话禁止并发生成
//   - 落库：user / assistant 消息的写入与终态收口
//   - Pre-Run 管线：记忆提取 → 上下文压缩 → 上下文重建
//   - 超时与取消：客户端断开后仍以 cancelled 落库，且必定释放锁
//   - 首轮异步标题：非关键副作用，失败不影响对话
//
// 单轮时序固定为四个阶段：Acquire → PreRun → Build&Run → Commit。
package harness

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"go.uber.org/zap"

	"mentorly/internal/agent"
	"mentorly/internal/config"
	"mentorly/internal/dao"
	"mentorly/internal/memory"
	"mentorly/internal/model"
	"mentorly/pkg/sse"
)

// 对外错误，供 handler 映射 HTTP 状态码。
var (
	// ErrSessionNotFound 会话不存在或不属于该用户（统一 404，避免泄露存在性）
	ErrSessionNotFound = errors.New("会话不存在")
	// ErrSessionBusy 会话正在生成中（409）
	ErrSessionBusy = errors.New("会话正在生成中，请稍后再试")
	// ErrEmptyQuestion 问题为空（400）
	ErrEmptyQuestion = errors.New("问题内容不能为空")
)

// Deps 是 Harness 的外部依赖。
type Deps struct {
	Config  *config.Config
	Chat    *dao.ChatRepo
	Memory  *dao.MemoryRepo
	Lock    *dao.LockRepo
	Builder *agent.Builder
	Context *memory.Builder
	Log     *zap.Logger
	// TitleGen 首轮标题生成，可为 nil 表示不生成
	TitleGen *TitleGenerator
}

// TutorHarness 编排单轮对话的完整生命周期。
type TutorHarness struct {
	cfg     *config.Config
	chat    *dao.ChatRepo
	mem     *dao.MemoryRepo
	lock    *dao.LockRepo
	builder *agent.Builder
	ctxb    *memory.Builder
	title   *TitleGenerator
	log     *zap.Logger
}

// New 构造 Harness。
func New(d Deps) *TutorHarness {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	return &TutorHarness{
		cfg:     d.Config,
		chat:    d.Chat,
		mem:     d.Memory,
		lock:    d.Lock,
		builder: d.Builder,
		ctxb:    d.Context,
		title:   d.TitleGen,
		log:     log,
	}
}

// Enabled 表示 Harness 是否可用（未配置模型时为 false，接口应返回 503）。
func (h *TutorHarness) Enabled() bool { return h.builder != nil && h.ctxb != nil }

// PreparedTurn 是阶段 1 的产物，承载本轮全部上下文。
type PreparedTurn struct {
	UserID    string
	SessionID string
	Question  string
	// UserMsgID 本轮 user 消息 id，构建历史时需排除
	UserMsgID uint64
	// IsFirstTurn 是否是会话首轮（用于触发标题生成）
	IsFirstTurn bool

	// release 释放会话锁，由 RunTurn 保证调用
	release func()
}

// Release 兜底释放锁。RunTurn 内部已释放，这里是防御性调用（幂等）。
func (t *PreparedTurn) Release() {
	if t != nil && t.release != nil {
		t.release()
		t.release = nil
	}
}

// PrepareTurn 阶段 1：加锁 → 归属校验 → 落库 user 消息。
//
// 必须在开启 SSE 之前完成：会话不存在(404)、无权访问(404)、
// 会话正在生成(409)、参数错误(400) 都要以标准 JSON 返回，
// 一旦写出 SSE 响应头就无法再改状态码。
func (h *TutorHarness) PrepareTurn(ctx context.Context, userID, sessionID, question string) (*PreparedTurn, error) {
	question = strings.TrimSpace(question)
	if question == "" {
		return nil, ErrEmptyQuestion
	}

	// 先校验会话归属，再做加锁：无效会话不该占用锁。
	if _, err := h.chat.GetSessionForUser(ctx, sessionID, userID); err != nil {
		if errors.Is(err, dao.ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	// 锁 TTL 覆盖整个 run_timeout 并留出余量：进程崩溃时锁能自动过期，
	// 不会把会话永久锁死。
	ttl := h.cfg.Chat.RunTimeout + 30*time.Second
	release, _, err := h.lock.Acquire(ctx, lockKey(sessionID), ttl)
	if err != nil {
		if errors.Is(err, dao.ErrLockBusy) {
			return nil, ErrSessionBusy
		}
		return nil, fmt.Errorf("获取会话锁失败: %w", err)
	}

	// 拿锁后重查会话：可能在上一步之后被删除。
	if _, err := h.chat.GetSessionForUser(ctx, sessionID, userID); err != nil {
		release()
		if errors.Is(err, dao.ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	// 判断是否首轮：在写入本轮消息之前统计。
	count, err := h.chat.CountMessages(ctx, sessionID)
	if err != nil {
		release()
		return nil, fmt.Errorf("统计消息失败: %w", err)
	}

	userMsg := &model.ChatMessage{
		SessionID: sessionID,
		Role:      model.RoleUser,
		Content:   question,
		Status:    model.StatusCompleted,
		Tokens:    memory.Counter{}.Estimate(question),
	}
	if err := h.chat.CreateMessage(ctx, userMsg); err != nil {
		release()
		return nil, fmt.Errorf("保存消息失败: %w", err)
	}

	// 更新最近活跃时间（失败不影响本轮）。
	_ = h.chat.TouchSession(ctx, sessionID, time.Now())

	return &PreparedTurn{
		UserID:      userID,
		SessionID:   sessionID,
		Question:    question,
		UserMsgID:   userMsg.ID,
		IsFirstTurn: count == 0,
		release:     release,
	}, nil
}

// RunTurn 阶段 2~4：PreRun → Build&Run → Commit。
//
// emit 用于向 SSE 写帧；即使客户端断开，也会用 WithoutCancel 落库。
func (h *TutorHarness) RunTurn(ctx context.Context, turn *PreparedTurn, emit func(sse.Frame)) {
	// 保证锁一定释放（无论成功、失败还是 panic）。
	defer turn.Release()

	// 单轮总超时。超过后取消 Agent，但落库仍走 WithoutCancel。
	runCtx, cancel := context.WithTimeout(ctx, h.cfg.Chat.RunTimeout)
	defer cancel()

	startedAt := time.Now()

	// ---------- 阶段 2：Pre-Run 上下文准备 ----------
	built, err := h.ctxb.Build(runCtx, memory.ContextRequest{
		UserID:          turn.UserID,
		SessionID:       turn.SessionID,
		CurrentMsgID:    turn.UserMsgID,
		CurrentQuestion: turn.Question,
		BasePrompt:      agent.BasePrompt(),
	})
	if err != nil {
		h.fail(runCtx, turn, emit, fmt.Errorf("准备上下文失败: %w", err))
		return
	}

	// ---------- 阶段 3：Build & Run Agent ----------
	workspace := h.cfg.Chat.SessionDir(turn.UserID, turn.SessionID)
	offload := h.cfg.Chat.OffloadDir(turn.UserID, turn.SessionID)

	runner, err := h.builder.Build(runCtx, agent.Spec{
		Instruction: built.Instruction,
		Workspace:   workspace,
		OffloadDir:  offload,
		MaxSteps:    h.cfg.Chat.MaxSteps,
	})
	if err != nil {
		h.fail(runCtx, turn, emit, fmt.Errorf("构建 Agent 失败: %w", err))
		return
	}

	// Scope 注入 context：Sandbox 与 remember 工具都从这里取身份与目录。
	runCtx = agent.WithScope(runCtx, agent.Scope{
		UserID:    turn.UserID,
		SessionID: turn.SessionID,
		Root:      workspace,
	})

	// 把 memory.Message 转成 agent.Message，再拼上本轮问题。
	history := make([]agent.Message, 0, len(built.Messages)+1)
	for _, m := range built.Messages {
		history = append(history, agent.Message{
			ID:      m.ID,
			Role:    m.Role,
			Content: m.Content,
			Status:  m.Status,
		})
	}
	history = append(history, agent.Message{
		ID:      turn.UserMsgID,
		Role:    model.RoleUser,
		Content: turn.Question,
		Status:  model.StatusCompleted,
	})

	msgs := agent.ToSchemaMessages(history)

	result, streamErr := agent.Stream(runCtx, runner, msgs, func(c agent.Chunk) error {
		if c.Reset {
			emit(sse.Reset())
			return nil
		}
		emit(sse.Delta(c.Text))
		return nil
	})

	// ---------- 阶段 4：Commit 终态收口 ----------
	elapsed := time.Since(startedAt)

	// 记录 Stream 的真实错误：否则失败轮次只能看到 "failed"，
	// 排障时分不清是模型报错、上下文超限还是空回答。
	if streamErr != nil {
		h.log.Warn("Agent 流式执行结束时有错误",
			zap.Error(streamErr),
			zap.String("session_id", turn.SessionID),
			zap.Int("answer_chars", len([]rune(answerOf(result)))),
			zap.Strings("tool_calls", toolCallsOf(result)),
		)
	}

	// 客户端断开时，Go 的 http 层可能还没报错（数据写进了内核缓冲），
	// 但 runCtx 已被 handler 主动取消。此时即使 streamErr 为 nil，
	// 本轮也必须按 cancelled 收口，否则会误记为 completed。
	if runCtx.Err() != nil && streamErr == nil {
		streamErr = runCtx.Err()
	}

	// 关键：即使 ctx 已取消，也要落库。用 WithoutCancel 断开取消信号传播。
	saveCtx, saveCancel := context.WithTimeout(context.WithoutCancel(ctx), 10*time.Second)
	defer saveCancel()

	status, content := resolveOutcome(result, streamErr, runCtx)
	assistantMsg := h.commit(saveCtx, turn, status, content, result, elapsed)

	// 本轮真实上下文用量写回会话，供下一轮阈值判断。
	if result != nil && result.Usage != nil && result.Usage.TotalTokens > 0 {
		if err := h.chat.UpdateContextTokens(saveCtx, turn.SessionID, result.Usage.TotalTokens); err != nil {
			h.log.Warn("更新上下文用量失败", zap.Error(err))
		}
	}

	// 终止帧。
	if streamErr != nil && !errors.Is(streamErr, context.Canceled) && !errors.Is(streamErr, context.DeadlineExceeded) {
		emit(sse.Error(userFacingError(streamErr)))
	}
	emit(sse.Done(assistantMsg.ID, status))

	// 首轮且成功完成：异步生成标题（不影响本轮结果）。
	if status == model.StatusCompleted && turn.IsFirstTurn && h.title != nil && content != "" {
		h.title.Enqueue(turn.SessionID, turn.Question, content)
	}

	h.log.Info("对话轮次结束",
		zap.String("session_id", turn.SessionID),
		zap.String("status", status),
		zap.Duration("elapsed", elapsed),
		zap.Int("answer_chars", len([]rune(content))),
	)
}

// commit 落库 assistant 消息并返回落库后的消息。
func (h *TutorHarness) commit(
	ctx context.Context,
	turn *PreparedTurn,
	status, content string,
	result *agent.StreamResult,
	elapsed time.Duration,
) *model.ChatMessage {
	msg := &model.ChatMessage{
		SessionID: turn.SessionID,
		Role:      model.RoleAssistant,
		Content:   content,
		Status:    status,
		Tokens:    memory.Counter{}.Estimate(content),
		Meta:      model.MessageMeta{ElapsedMS: elapsed.Milliseconds()},
	}

	if result != nil && result.Usage != nil {
		// assistant 消息的 tokens 回填真实 CompletionTokens（无则用估算值）。
		if result.Usage.CompletionTokens > 0 {
			msg.Tokens = result.Usage.CompletionTokens
		}
		msg.Meta.Usage = &model.TokenUsage{
			PromptTokens:     result.Usage.PromptTokens,
			CompletionTokens: result.Usage.CompletionTokens,
			TotalTokens:      result.Usage.TotalTokens,
		}
	}

	if err := h.chat.CreateMessage(ctx, msg); err != nil {
		h.log.Error("落库 assistant 消息失败", zap.Error(err), zap.String("status", status))
	}

	_ = h.chat.TouchSession(ctx, turn.SessionID, time.Now())
	return msg
}

// fail 处理 Pre-Run 或 Agent 构建阶段的失败。
func (h *TutorHarness) fail(ctx context.Context, turn *PreparedTurn, emit func(sse.Frame), err error) {
	h.log.Error("本轮对话失败",
		zap.Error(err),
		zap.String("session_id", turn.SessionID),
	)

	// 即使失败也落库一条失败消息，保证历史完整、游标不悬空。
	saveCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 5*time.Second)
	defer cancel()

	msg := &model.ChatMessage{
		SessionID: turn.SessionID,
		Role:      model.RoleAssistant,
		Content:   "",
		Status:    model.StatusFailed,
		Meta:      model.MessageMeta{Error: err.Error()},
	}
	if createErr := h.chat.CreateMessage(saveCtx, msg); createErr != nil {
		h.log.Error("落库失败消息出错", zap.Error(createErr))
	}

	emit(sse.Error(userFacingError(err)))
	emit(sse.Done(msg.ID, model.StatusFailed))
}

// resolveOutcome 根据流式结果与错误判定终态。
func resolveOutcome(result *agent.StreamResult, streamErr error, runCtx context.Context) (status, content string) {
	answer := ""
	if result != nil {
		answer = result.Answer
	}

	switch {
	case streamErr == nil:
		// 工具轮次后模型可能不再输出文本：给一个明确占位，
		// 避免前端渲染出一条空消息。
		if strings.TrimSpace(answer) == "" {
			answer = "[已完成工具操作]"
		}
		return model.StatusCompleted, answer

	case errors.Is(streamErr, context.Canceled),
		errors.Is(streamErr, context.DeadlineExceeded),
		runCtx.Err() != nil:
		// 客户端断开或超时：保留已生成的半截文本，空时写入占位说明。
		if strings.TrimSpace(answer) == "" {
			answer = "[本轮生成已停止]"
		}
		return model.StatusCancelled, answer

	default:
		return model.StatusFailed, answer
	}
}

// answerOf 安全取最终回答，便于日志。
func answerOf(res *agent.StreamResult) string {
	if res == nil {
		return ""
	}
	return res.Answer
}

// toolCallsOf 安全取工具调用名。
func toolCallsOf(res *agent.StreamResult) []string {
	if res == nil {
		return nil
	}
	return res.ToolCalls
}

// userFacingError 把内部错误转成可展示的简短信息，避免泄露实现细节。
func userFacingError(err error) string {
	switch {
	case errors.Is(err, agent.ErrEmptyAnswer):
		return "模型未返回有效回答，请重试"
	case errors.Is(err, context.DeadlineExceeded):
		return "本轮生成超时"
	default:
		return "生成失败，请稍后重试"
	}
}

// lockKey 返回会话锁的 Redis key。
func lockKey(sessionID string) string {
	return "chat:lock:" + sessionID
}
