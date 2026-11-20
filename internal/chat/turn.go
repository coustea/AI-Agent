package chat

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"go.uber.org/zap"

	"mentorly/internal/infra"
)

// 一轮对话对外错误，供传输层映射状态码。
var (
	// ErrBusy 会话正在生成中（409）
	ErrBusy = errors.New("会话正在生成中，请稍后再试")
	// ErrEmptyQuestion 问题为空（400）
	ErrEmptyQuestion = errors.New("问题内容不能为空")
	// ErrUnavailable 对话能力未启用（503）
	ErrUnavailable = errors.New("对话能力未启用")
	// ErrLockBusy 会话锁被占用，由 Lock 实现返回
	ErrLockBusy = errors.New("lock busy")
)

// Turn 是一轮进行中的对话。
//
// 生命周期：Begin 加锁并落库用户消息 → Run 执行并收口 → Close 释放锁。
// Close 幂等，必须由调用方 defer：
//
//	t, err := svc.Begin(...)
//	if err != nil { /* 404/409/400/503 */ }
//	defer t.Close()
//	t.Run(ctx, sink)
type Turn struct {
	svc       *Service
	userID    string
	sessionID string
	question  string

	// userMsgID 本轮 user 消息 id，构建历史时需排除
	userMsgID uint64
	// isFirstTurn 是否会话首轮，用于触发标题生成
	isFirstTurn bool

	release func()
}

// Begin 阶段 1：加锁 → 归属校验 → 落库用户消息。
//
// 必须在开启 SSE 之前完成：会话不存在(404)、会话正在生成(409)、
// 参数错误(400) 都要以标准 JSON 返回，一旦写出流式响应头就无法再改状态码。
func (s *Service) Begin(ctx context.Context, userID, sessionID, question string) (*Turn, error) {
	if !s.Enabled() {
		return nil, ErrUnavailable
	}

	question = strings.TrimSpace(question)
	if question == "" {
		return nil, ErrEmptyQuestion
	}

	// 先校验会话归属，再加锁：无效会话不该占用锁。
	if _, err := s.store.GetSessionForUser(ctx, sessionID, userID); err != nil {
		if errors.Is(err, ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	// 锁 TTL 覆盖整个 run_timeout 并留出余量：进程崩溃时锁能自动过期，
	// 不会把会话永久锁死。
	ttl := s.cfg.RunTimeout + 30*time.Second
	release, err := s.lock.Acquire(ctx, lockKey(sessionID), ttl)
	if err != nil {
		if errors.Is(err, infra.ErrLockBusy) {
			return nil, ErrBusy
		}
		return nil, fmt.Errorf("获取会话锁失败: %w", err)
	}

	// 拿锁后重查会话：可能在上一步之后被删除。
	if _, err := s.store.GetSessionForUser(ctx, sessionID, userID); err != nil {
		release()
		if errors.Is(err, ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	// 判断是否首轮：在写入本轮消息之前统计。
	count, err := s.store.CountMessages(ctx, sessionID)
	if err != nil {
		release()
		return nil, fmt.Errorf("统计消息失败: %w", err)
	}

	userMsg := &Message{
		Role:    RoleUser,
		Content: question,
		Status:  StatusCompleted,
	}
	if err := s.store.CreateMessage(ctx, sessionID, userMsg, s.counter.Estimate(question), MessageMeta{}); err != nil {
		release()
		return nil, fmt.Errorf("保存消息失败: %w", err)
	}

	// 更新最近活跃时间（失败不影响本轮）。
	_ = s.store.TouchSession(ctx, sessionID, time.Now())

	return &Turn{
		svc:         s,
		userID:      userID,
		sessionID:   sessionID,
		question:    question,
		userMsgID:   userMsg.ID,
		isFirstTurn: count == 0,
		release:     release,
	}, nil
}

// Close 释放会话锁。
//
// 幂等：Run 内部已经释放，这里兜底是为了让调用方能无条件 defer。
func (t *Turn) Close() {
	if t == nil || t.release == nil {
		return
	}
	t.release()
	t.release = nil
}

// Result 是一轮的实际结果。
type Result struct {
	// MessageID 落库后的 assistant 消息 id（未落库时为 0）
	MessageID uint64
	// Status 终态：completed / failed / cancelled
	Status string
	// Content 落库的回答内容
	Content string
}

// Run 执行本轮：准备上下文 → 调 Agent → 收口落库。
//
// sink 接收增量片段；即使客户端断开，也会用 WithoutCancel 落库。
// 返回本轮结果，供传输层拼 done 帧与测试断言。
func (t *Turn) Run(ctx context.Context, sink func(Chunk) error) Result {
	// 保证锁一定释放（无论成功、失败还是 panic）。
	defer t.Close()

	s := t.svc

	// 单轮总超时。超过后取消 Agent，但落库仍走 WithoutCancel。
	runCtx, cancel := context.WithTimeout(ctx, s.cfg.RunTimeout)
	defer cancel()

	startedAt := time.Now()

	// ---------- 阶段 2：Pre-Run 上下文准备 ----------
	instruction, history, err := s.prepare(runCtx, t)
	if err != nil {
		return s.finishFailed(runCtx, t, sink, fmt.Errorf("准备上下文失败: %w", err))
	}

	// ---------- 阶段 3：执行 Agent ----------
	runner, err := s.agent.build(runCtx, runnerSpec{
		Instruction: instruction,
		Workspace:   s.workspace(t.userID, t.sessionID),
		OffloadDir:  s.offload(t.userID, t.sessionID),
		MaxSteps:    s.cfg.MaxSteps,
	})
	if err != nil {
		return s.finishFailed(runCtx, t, sink, fmt.Errorf("构建 Agent 失败: %w", err))
	}

	// 历史消息 + 本轮问题
	msgs := append(history, Message{
		ID:      t.userMsgID,
		Role:    RoleUser,
		Content: t.question,
		Status:  StatusCompleted,
	})

	result, streamErr := Stream(runCtx, runner, ToSchemaMessages(msgs), sink)

	// ---------- 阶段 4：Commit 终态收口 ----------
	elapsed := time.Since(startedAt)

	// 记录 Stream 的真实错误：否则失败轮次只能看到 "failed"，
	// 排障时分不清是模型报错、上下文超限还是空回答。
	if streamErr != nil {
		s.log.Warn("Agent 流式执行结束时有错误",
			zap.Error(streamErr),
			zap.String("session_id", t.sessionID),
			zap.Strings("tool_calls", toolCallsOf(result)),
		)
	}

	status, content := resolveOutcome(result, streamErr, runCtx)

	// 关键：即使 ctx 已取消，也要落库。用 WithoutCancel 断开取消信号传播。
	saveCtx, saveCancel := context.WithTimeout(context.WithoutCancel(ctx), 10*time.Second)
	defer saveCancel()

	msgID, usage := s.commit(saveCtx, t, status, content, result, elapsed)

	// 本轮真实上下文用量写回会话，供下一轮阈值判断。
	if usage != nil && usage.TotalTokens > 0 {
		if err := s.store.UpdateContextTokens(saveCtx, t.sessionID, usage.TotalTokens); err != nil {
			s.log.Warn("更新上下文用量失败", zap.Error(err))
		}
	}

	s.log.Info("对话轮次结束",
		zap.String("session_id", t.sessionID),
		zap.String("status", status),
		zap.Uint64("message_id", msgID),
		zap.Duration("elapsed", elapsed),
		zap.Int("answer_chars", len([]rune(content))),
	)

	// 首轮且成功完成：异步生成标题（不影响本轮结果）。
	if status == StatusCompleted && t.isFirstTurn && s.title != nil && content != "" {
		s.title.Enqueue(t.sessionID, t.question, content)
	}

	return Result{MessageID: msgID, Status: status, Content: content}
}

// prepare 是 Pre-Run 管线：压缩上下文 → 重建窗口与 Prompt。
//
// 顺序不可交换：先压缩，重建时读到的才是压缩后的最小历史。
func (s *Service) prepare(ctx context.Context, t *Turn) (instruction string, history []Message, err error) {
	base := BasePrompt()

	// 先估算一次动态 System Prompt 的规模，供压缩阈值判断使用。
	// 此时的摘要是「压缩前」的版本，只用于判断是否超阈值。
	systemTokens := s.counter.Estimate(BuildPrompt(base, "", nil))

	// 读会话（含当前摘要与游标）。
	sess, err := s.store.GetSession(ctx, t.sessionID)
	if err != nil {
		return "", nil, fmt.Errorf("读取会话失败: %w", err)
	}

	// 压缩游标之后的消息即为未压缩历史。
	after, err := s.store.ListMessagesAfter(ctx, t.sessionID, sess.SummaryCursor)
	if err != nil {
		return "", nil, fmt.Errorf("读取历史消息失败: %w", err)
	}

	// 排除本轮当前消息与空的失败消息——当前问题会单独追加。
	candidates := make([]Message, 0, len(after))
	for _, m := range after {
		if m.ID == t.userMsgID || m.IsEmptyFailure() {
			continue
		}
		candidates = append(candidates, m)
	}

	// 第 1 步：上下文滚动压缩。
	s.MaybeRun(ctx, sess, candidates, t.question, systemTokens)

	// 第 2 步：用最新状态重建上下文。
	// 压缩可能刚推进了游标与摘要，必须重读会话而不是复用上面的 sess。
	sess, err = s.store.GetSession(ctx, t.sessionID)
	if err != nil {
		return "", nil, fmt.Errorf("读取会话失败: %w", err)
	}

	history, err = s.store.ListMessagesAfter(ctx, t.sessionID, sess.SummaryCursor)
	if err != nil {
		return "", nil, fmt.Errorf("读取历史消息失败: %w", err)
	}

	kept := make([]Message, 0, len(history))
	for _, m := range history {
		if m.ID == t.userMsgID || m.IsEmptyFailure() {
			continue
		}
		kept = append(kept, m)
	}

	files := ListWorkspaceFiles(s.cfg.WorkspaceDir, sess.UserID, sess.ID)
	instruction = BuildPrompt(base, sess.Summary, files)
	systemTokens = s.counter.Estimate(instruction)

	// 历史预算 = 总预算 - System Prompt - 本轮问题。
	budget := s.cfg.HistoryBudgetTokens - systemTokens - s.counter.Estimate(t.question)
	fitted, _ := Fit(kept, Budget{
		MaxMessages: s.cfg.HistoryMaxMessages,
		Tokens:      budget,
	}, s.counter)

	return instruction, fitted, nil
}

// commit 落库 assistant 消息并返回消息 id 与用量。
func (s *Service) commit(
	ctx context.Context,
	t *Turn,
	status, content string,
	result *StreamResult,
	elapsed time.Duration,
) (uint64, *TokenUsage) {
	msg := &Message{
		Role:    RoleAssistant,
		Content: content,
		Status:  status,
	}
	tokens := s.counter.Estimate(content)
	meta := MessageMeta{ElapsedMS: elapsed.Milliseconds()}

	var usage *TokenUsage
	if result != nil && result.Usage != nil {
		usage = &TokenUsage{
			PromptTokens:     result.Usage.PromptTokens,
			CompletionTokens: result.Usage.CompletionTokens,
			TotalTokens:      result.Usage.TotalTokens,
		}
		// assistant 消息的 tokens 回填真实 CompletionTokens（无则用估算值）。
		if result.Usage.CompletionTokens > 0 {
			tokens = result.Usage.CompletionTokens
		}
		meta.Usage = usage
	}

	if err := s.store.CreateMessage(ctx, t.sessionID, msg, tokens, meta); err != nil {
		s.log.Error("落库 assistant 消息失败", zap.Error(err), zap.String("status", status))
	}

	_ = s.store.TouchSession(ctx, t.sessionID, time.Now())
	return msg.ID, usage
}

// finishFailed 处理 Pre-Run 或 Agent 构建阶段的失败。
func (s *Service) finishFailed(ctx context.Context, t *Turn, sink func(Chunk) error, err error) Result {
	s.log.Error("本轮对话失败", zap.Error(err), zap.String("session_id", t.sessionID))

	// 即使失败也落库一条失败消息，保证历史完整、游标不悬空。
	saveCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 5*time.Second)
	defer cancel()

	msg := &Message{
		Role:    RoleAssistant,
		Content: "",
		Status:  StatusFailed,
	}
	var msgID uint64
	if createErr := s.store.CreateMessage(saveCtx, t.sessionID, msg, 0, MessageMeta{Error: err.Error()}); createErr != nil {
		s.log.Error("落库失败消息出错", zap.Error(createErr))
	} else {
		msgID = msg.ID
	}

	// 通知客户端：错误信息 + 结束。Done 帧由传输层在 Run 返回后统一发送。
	if sink != nil {
		_ = sink(Chunk{Text: userFacingError(err), Reset: true})
	}

	return Result{MessageID: msgID, Status: StatusFailed}
}

// resolveOutcome 根据流式结果与错误判定终态。
//
// 顺序关键：ctx 已取消必须优先于 streamErr == nil 判断。
//
// 客户端断开时，写失败发生在传输层，Stream 本身可能正常返回 nil 错误，
// 但 ctx 已经被调用方取消。若先判 streamErr == nil，这一轮会被误记为
// completed——用户看到的是"回答完整"，实际只收到半截。
func resolveOutcome(result *StreamResult, streamErr error, runCtx context.Context) (status, content string) {
	answer := ""
	if result != nil {
		answer = result.Answer
	}

	cancelled := errors.Is(streamErr, context.Canceled) ||
		errors.Is(streamErr, context.DeadlineExceeded) ||
		runCtx.Err() != nil

	if cancelled {
		// 客户端断开或超时：保留已生成的半截文本，空时写入占位说明。
		if strings.TrimSpace(answer) == "" {
			answer = "[本轮生成已停止]"
		}
		return StatusCancelled, answer
	}

	if streamErr == nil {
		// 工具轮次后模型可能不再输出文本：给一个明确占位，
		// 避免前端渲染出一条空消息。
		if strings.TrimSpace(answer) == "" {
			answer = "[已完成工具操作]"
		}
		return StatusCompleted, answer
	}

	return StatusFailed, answer
}

// toolCallsOf 安全取工具调用名。
func toolCallsOf(res *StreamResult) []string {
	if res == nil {
		return nil
	}
	return res.ToolCalls
}

// userFacingError 把内部错误转成可展示的简短信息，避免泄露实现细节。
func userFacingError(err error) string {
	switch {
	case errors.Is(err, ErrEmptyAnswer):
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
