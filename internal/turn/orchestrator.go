package turn

import (
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"strings"
	"time"

	"go.uber.org/zap"

	"mentorly/internal/agent"
	"mentorly/internal/chat"
	"mentorly/internal/dialogue"
	"mentorly/internal/memory"
	"mentorly/internal/window"
)

// Config 是编排一轮对话所需的全部参数。
type Config struct {
	// RunTimeout 单轮总超时
	RunTimeout time.Duration
	// MaxSteps Agent 单轮最大迭代步数
	MaxSteps int
	// HistoryMaxMessages 历史条数上限
	HistoryMaxMessages int
	// HistoryBudgetTokens 历史 token 预算
	HistoryBudgetTokens int
	// WorkspaceDir 会话工作目录根路径
	WorkspaceDir string
	// OffloadDir 工具结果卸载根目录
	OffloadDir string
	// SkillsDir 技能目录
	SkillsDir string
	// MemoryMaxChars 长期记忆字符上限
	MemoryMaxChars int
	// TitleTimeout 标题生成超时
	TitleTimeout time.Duration
}

// Lock 是会话互斥锁能力。
type Lock interface {
	// Acquire 尝试获取锁，返回释放函数。
	// 拿不到时返回聊胜于无的错误，由编排层翻译成 ErrBusy。
	Acquire(ctx context.Context, key string, ttl time.Duration) (release func(), err error)
}

// TitleScheduler 触发首轮标题的异步生成。
type TitleScheduler interface {
	Enqueue(sessionID, question, answer string)
}

// Deps 是编排器的外部依赖。
type Deps struct {
	Config   Config
	Sessions *chat.Repo
	Digest   *memory.Digest
	Memory   *memory.Consolidator
	Docs     memory.Store
	Lock     Lock
	Builder  *agent.Builder
	Title    TitleScheduler
	Log      *zap.Logger
}

// Orchestrator 编排一轮对话的完整生命周期。
type Orchestrator struct {
	cfg      Config
	sessions *chat.Repo
	digest   *memory.Digest
	memory   *memory.Consolidator
	lock     Lock
	builder  *agent.Builder
	title    TitleScheduler
	// docs 读取长期记忆文档，用于注入 System Prompt。
	// 与 digest/memory 分开：那两个是「写」的职责，这里只需要「读」。
	docs    memory.Store
	counter window.Counter
	log     *zap.Logger
}

// New 构造编排器。
func New(d Deps) *Orchestrator {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	cfg := d.Config
	if cfg.RunTimeout <= 0 {
		cfg.RunTimeout = 600 * time.Second
	}
	if cfg.MaxSteps <= 0 {
		cfg.MaxSteps = 8
	}
	if cfg.HistoryBudgetTokens <= 0 {
		cfg.HistoryBudgetTokens = 12000
	}
	if cfg.HistoryMaxMessages <= 0 {
		cfg.HistoryMaxMessages = 40
	}
	return &Orchestrator{
		cfg:      cfg,
		sessions: d.Sessions,
		digest:   d.Digest,
		memory:   d.Memory,
		docs:     d.Docs,
		lock:     d.Lock,
		builder:  d.Builder,
		title:    d.Title,
		counter:  window.Counter{},
		log:      log,
	}
}

// Enabled 表示对话能力是否可用（未配置模型时为 false，接口应返回 503）。
func (o *Orchestrator) Enabled() bool {
	return o != nil && o.builder != nil && o.sessions != nil
}

// Prepare 阶段 1：加锁 → 归属校验 → 落库用户消息。
//
// 必须在开启 SSE 之前完成：会话不存在(404)、无权访问(404)、
// 会话正在生成(409)、参数错误(400) 都要以标准 JSON 返回，
// 一旦写出流式响应头就无法再改状态码。
func (o *Orchestrator) Prepare(ctx context.Context, userID, sessionID, question string) (*Prepared, error) {
	if !o.Enabled() {
		return nil, ErrUnavailable
	}

	question = strings.TrimSpace(question)
	if question == "" {
		return nil, ErrEmptyQuestion
	}

	// 先校验会话归属，再做加锁：无效会话不该占用锁。
	if _, err := o.sessions.GetSessionForUser(ctx, sessionID, userID); err != nil {
		if errors.Is(err, chat.ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	// 锁 TTL 覆盖整个 run_timeout 并留出余量：进程崩溃时锁能自动过期，
	// 不会把会话永久锁死。
	ttl := o.cfg.RunTimeout + 30*time.Second
	release, err := o.lock.Acquire(ctx, lockKey(sessionID), ttl)
	if err != nil {
		if errors.Is(err, ErrLockBusy) {
			return nil, ErrBusy
		}
		return nil, fmt.Errorf("获取会话锁失败: %w", err)
	}

	// 拿锁后重查会话：可能在上一步之后被删除。
	if _, err := o.sessions.GetSessionForUser(ctx, sessionID, userID); err != nil {
		release()
		if errors.Is(err, chat.ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	// 判断是否首轮：在写入本轮消息之前统计。
	count, err := o.sessions.CountMessages(ctx, sessionID)
	if err != nil {
		release()
		return nil, fmt.Errorf("统计消息失败: %w", err)
	}

	userMsg := &dialogue.Message{
		Role:    dialogue.RoleUser,
		Content: question,
		Status:  dialogue.StatusCompleted,
	}
	tokens := o.counter.Estimate(question)
	if err := o.sessions.CreateMessage(ctx, sessionID, userMsg, tokens, chat.MessageMeta{}); err != nil {
		release()
		return nil, fmt.Errorf("保存消息失败: %w", err)
	}

	// 更新最近活跃时间（失败不影响本轮）。
	_ = o.sessions.TouchSession(ctx, sessionID, time.Now())

	return &Prepared{
		UserID:      userID,
		SessionID:   sessionID,
		Question:    question,
		UserMsgID:   userMsg.ID,
		IsFirstTurn: count == 0,
		release:     release,
	}, nil
}

// Run 阶段 2~4：Prepare → Run → Commit。
//
// sink 接收本轮事件；即使客户端断开，也会用 WithoutCancel 落库。
// 返回 Outcome 供调用方记录与测试断言。
func (o *Orchestrator) Run(ctx context.Context, p *Prepared, sink Sink) Outcome {
	// 保证锁一定释放（无论成功、失败还是 panic）。
	defer p.Release()

	// 单轮总超时。超过后取消 Agent，但落库仍走 WithoutCancel。
	runCtx, cancel := context.WithTimeout(ctx, o.cfg.RunTimeout)
	defer cancel()

	startedAt := time.Now()

	// ---------- 阶段 2：Pre-Run 上下文准备 ----------
	built, err := o.prepareContext(runCtx, p)
	if err != nil {
		return o.fail(runCtx, p, sink, fmt.Errorf("准备上下文失败: %w", err))
	}

	// ---------- 阶段 3：Build & Run Agent ----------
	runner, err := o.builder.Build(runCtx, agent.Spec{
		Instruction: built.Instruction,
		Workspace:   o.workspace(p.UserID, p.SessionID),
		OffloadDir:  o.offload(p.UserID, p.SessionID),
		MaxSteps:    o.cfg.MaxSteps,
	})
	if err != nil {
		return o.fail(runCtx, p, sink, fmt.Errorf("构建 Agent 失败: %w", err))
	}

	// Scope 注入 context：Sandbox 与 remember 工具都从这里取身份与目录。
	runCtx = agent.WithScope(runCtx, agent.Scope{
		UserID:    p.UserID,
		SessionID: p.SessionID,
		Root:      o.workspace(p.UserID, p.SessionID),
	})

	// 历史消息 + 本轮问题。
	history := make([]dialogue.Message, 0, len(built.Messages)+1)
	history = append(history, built.Messages...)
	history = append(history,
		dialogue.Message{
			ID:      p.UserMsgID,
			Role:    dialogue.RoleUser,
			Content: p.Question,
			Status:  dialogue.StatusCompleted,
		},
		// 占位：Build 返回的 Instruction 已含全部动态段落
	)

	msgs := agent.ToSchemaMessages(history)

	result, streamErr := agent.Stream(runCtx, runner, msgs, func(c agent.Chunk) error {
		if c.Reset {
			sink(Event{Kind: EventReset})
			return nil
		}
		sink(Event{Kind: EventDelta, Text: c.Text})
		return nil
	})

	// ---------- 阶段 4：Commit 终态收口 ----------
	elapsed := time.Since(startedAt)

	// 记录 Stream 的真实错误：否则失败轮次只能看到 "failed"，
	// 排障时分不清是模型报错、上下文超限还是空回答。
	if streamErr != nil {
		o.log.Warn("Agent 流式执行结束时有错误",
			zap.Error(streamErr),
			zap.String("session_id", p.SessionID),
			zap.Strings("tool_calls", toolCallsOf(result)),
		)
	}

	// 客户端断开时，Go 的 http 层可能还没报错（数据写进了内核缓冲），
	// 但 runCtx 已被调用方主动取消。此时即使 streamErr 为 nil，
	// 本轮也必须按 cancelled 收口，否则会误记为 completed。
	if runCtx.Err() != nil && streamErr == nil {
		streamErr = runCtx.Err()
	}

	status, content := resolveOutcome(result, streamErr, runCtx)

	// 关键：即使 ctx 已取消，也要落库。用 WithoutCancel 断开取消信号传播。
	saveCtx, saveCancel := context.WithTimeout(context.WithoutCancel(ctx), 10*time.Second)
	defer saveCancel()

	msgID, usage := o.commit(saveCtx, p, status, content, result, elapsed)

	// 本轮真实上下文用量写回会话，供下一轮阈值判断。
	if usage != nil && usage.TotalTokens > 0 {
		if err := o.sessions.UpdateContextTokens(saveCtx, p.SessionID, usage.TotalTokens); err != nil {
			o.log.Warn("更新上下文用量失败", zap.Error(err))
		}
	}

	// 终止帧。
	if streamErr != nil && !errors.Is(streamErr, context.Canceled) && !errors.Is(streamErr, context.DeadlineExceeded) {
		sink(Event{Kind: EventError, Text: userFacingError(streamErr)})
	}
	sink(Event{Kind: EventDone, MessageID: msgID, Status: status})

	// 首轮且成功完成：异步生成标题（不影响本轮结果）。
	if status == dialogue.StatusCompleted && p.IsFirstTurn && o.title != nil && content != "" {
		o.title.Enqueue(p.SessionID, p.Question, content)
	}

	o.log.Info("对话轮次结束",
		zap.String("session_id", p.SessionID),
		zap.String("status", status),
		zap.Duration("elapsed", elapsed),
		zap.Int("answer_chars", len([]rune(content))),
	)

	return Outcome{
		Status:    status,
		Content:   content,
		Elapsed:   elapsed,
		Usage:     usage,
		ToolCalls: toolCallsOf(result),
	}
}

// BuiltContext 是 Pre-Run 的产物。
type BuiltContext struct {
	// Instruction 已组装好的完整动态 System Prompt
	Instruction string
	// Messages 预算截断后的历史消息（不含本轮当前问题）
	Messages []dialogue.Message
	// Summary 本轮使用的会话摘要
	Summary string
	// MemoryDoc 本轮使用的长期记忆
	MemoryDoc string
	// HistoryTokens 历史消息的估算 token 数
	HistoryTokens int
}

// prepareContext 严格执行三步管线：记忆提取 → 上下文压缩 → 重建窗口。
//
// 顺序不可交换：先提取记忆，才能在压缩丢弃原文前保住长期信息；
// 先压缩，重建时读到的才是压缩后的最小历史。
func (o *Orchestrator) prepareContext(ctx context.Context, p *Prepared) (*BuiltContext, error) {
	base := agent.BasePrompt()

	// 先估算一次动态 System Prompt 的规模，供压缩阈值判断使用。
	// 此时的记忆/摘要还是「压缩前」的版本，只用于判断是否超阈值。
	preSystem := agent.BuildPrompt(base, "", "", nil)
	systemTokens := o.counter.Estimate(preSystem)

	// 第 1 步：长期记忆提取。
	// 先探一下本次是否会压缩，让整合器能在原文被丢弃前抢跑。
	if o.memory != nil {
		willCompress := o.peekCompress(ctx, p)
		o.memory.MaybeRun(ctx, p.SessionID, p.UserMsgID, willCompress)
	}

	// 第 2 步：上下文滚动压缩。
	if o.digest != nil {
		o.digest.MaybeRun(ctx, p.SessionID, p.UserMsgID, p.Question, systemTokens)
	}

	// 第 3 步：用最新状态重建上下文。
	sess, err := o.sessions.GetSession(ctx, p.SessionID)
	if err != nil {
		return nil, fmt.Errorf("读取会话失败: %w", err)
	}

	memoryDoc := ""
	if o.docs != nil {
		doc, err := o.docs.Get(ctx, sess.UserID)
		if err != nil {
			return nil, fmt.Errorf("读取长期记忆失败: %w", err)
		}
		// 空小节会白占 token，注入前先剔除。
		memoryDoc = memory.PruneEmptySections(doc.Content)
	}

	// 压缩游标之后的消息即为剩余历史。
	history, err := o.sessions.ListMessagesAfter(ctx, p.SessionID, sess.SummaryCursor)
	if err != nil {
		return nil, fmt.Errorf("读取历史消息失败: %w", err)
	}

	// 排除本轮当前消息与空的失败消息——当前问题会单独追加。
	candidates := make([]dialogue.Message, 0, len(history))
	for _, m := range history {
		if m.ID == p.UserMsgID || m.IsEmptyFailure() {
			continue
		}
		candidates = append(candidates, m)
	}

	files := memory.ListWorkspaceFiles(o.cfg.WorkspaceDir, sess.UserID, sess.ID)
	instruction := agent.BuildPrompt(base, memoryDoc, sess.Summary, files)
	systemTokens = o.counter.Estimate(instruction)

	// 历史预算 = 总预算 - System Prompt - 本轮问题。
	budget := o.cfg.HistoryBudgetTokens - systemTokens - o.counter.Estimate(p.Question)
	kept, keptTokens := window.Fit(candidates, window.Budget{
		MaxMessages: o.cfg.HistoryMaxMessages,
		Tokens:      budget,
	}, o.counter)

	return &BuiltContext{
		Instruction:   instruction,
		Messages:      kept,
		Summary:       sess.Summary,
		MemoryDoc:     memoryDoc,
		HistoryTokens: keptTokens,
	}, nil
}

// peekCompress 用压缩前状态判断本次 Pre-Run 是否会触发压缩。
func (o *Orchestrator) peekCompress(ctx context.Context, p *Prepared) bool {
	if o.digest == nil {
		return false
	}
	sess, err := o.sessions.GetSession(ctx, p.SessionID)
	if err != nil {
		return false
	}
	msgs, err := o.sessions.ListMessagesAfter(ctx, p.SessionID, sess.SummaryCursor)
	if err != nil {
		return false
	}

	filtered := make([]dialogue.Message, 0, len(msgs))
	for _, m := range msgs {
		if m.ID == p.UserMsgID {
			continue
		}
		filtered = append(filtered, m)
	}

	ok, _ := o.digest.ShouldCompress(memory.Uncompressed{
		Summary:         sess.Summary,
		ContextTokens:   sess.ContextTokens,
		Messages:        filtered,
		CurrentQuestion: p.Question,
	})
	return ok
}

// commit 落库 assistant 消息并返回消息 id 与用量。
func (o *Orchestrator) commit(
	ctx context.Context,
	p *Prepared,
	status, content string,
	result *agent.StreamResult,
	elapsed time.Duration,
) (uint64, *TokenUsage) {
	msg := &dialogue.Message{
		Role:    dialogue.RoleAssistant,
		Content: content,
		Status:  status,
	}
	tokens := o.counter.Estimate(content)
	meta := chat.MessageMeta{ElapsedMS: elapsed.Milliseconds()}

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
		meta.Usage = &chat.TokenUsage{
			PromptTokens:     result.Usage.PromptTokens,
			CompletionTokens: result.Usage.CompletionTokens,
			TotalTokens:      result.Usage.TotalTokens,
		}
	}

	if err := o.sessions.CreateMessage(ctx, p.SessionID, msg, tokens, meta); err != nil {
		o.log.Error("落库 assistant 消息失败", zap.Error(err), zap.String("status", status))
	}

	_ = o.sessions.TouchSession(ctx, p.SessionID, time.Now())
	return msg.ID, usage
}

// fail 处理 Pre-Run 或 Agent 构建阶段的失败。
func (o *Orchestrator) fail(ctx context.Context, p *Prepared, sink Sink, err error) Outcome {
	o.log.Error("本轮对话失败", zap.Error(err), zap.String("session_id", p.SessionID))

	// 即使失败也落库一条失败消息，保证历史完整、游标不悬空。
	saveCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 5*time.Second)
	defer cancel()

	msg := &dialogue.Message{
		Role:    dialogue.RoleAssistant,
		Content: "",
		Status:  dialogue.StatusFailed,
	}
	var msgID uint64
	if createErr := o.sessions.CreateMessage(saveCtx, p.SessionID, msg, 0, chat.MessageMeta{Error: err.Error()}); createErr != nil {
		o.log.Error("落库失败消息出错", zap.Error(createErr))
	} else {
		msgID = msg.ID
	}

	sink(Event{Kind: EventError, Text: userFacingError(err)})
	sink(Event{Kind: EventDone, MessageID: msgID, Status: dialogue.StatusFailed})

	return Outcome{Status: dialogue.StatusFailed}
}

// resolveOutcome 根据流式结果与错误判定终态。
func resolveOutcome(result *agent.StreamResult, streamErr error, runCtx context.Context) (status, content string) {
	answer := ""
	if result != nil {
		answer = result.Answer
	}

	// 顺序关键：ctx 已取消必须优先于 streamErr == nil 判断。
	//
	// 客户端断开时，写失败发生在传输层，Stream 本身可能正常返回 nil 错误，
	// 但 ctx 已经被调用方取消。若先判 streamErr == nil，这一轮会被误记为
	// completed——用户看到的是"回答完整"，实际只收到半截。
	cancelled := errors.Is(streamErr, context.Canceled) ||
		errors.Is(streamErr, context.DeadlineExceeded) ||
		runCtx.Err() != nil

	if cancelled {
		// 客户端断开或超时：保留已生成的半截文本，空时写入占位说明。
		if strings.TrimSpace(answer) == "" {
			answer = "[本轮生成已停止]"
		}
		return dialogue.StatusCancelled, answer
	}

	if streamErr == nil {
		// 工具轮次后模型可能不再输出文本：给一个明确占位，
		// 避免前端渲染出一条空消息。
		if strings.TrimSpace(answer) == "" {
			answer = "[已完成工具操作]"
		}
		return dialogue.StatusCompleted, answer
	}

	return dialogue.StatusFailed, answer
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

// pathJoin 拼装目录路径。抽成函数便于统一处理空 root。
func pathJoin(root string, parts ...string) string {
	all := append([]string{root}, parts...)
	return filepath.Join(all...)
}

// workspace 返回会话工作目录。
func (o *Orchestrator) workspace(userID, sessionID string) string {
	return pathJoin(o.cfg.WorkspaceDir, userID, sessionID)
}

// offload 返回工具结果卸载目录。
func (o *Orchestrator) offload(userID, sessionID string) string {
	return pathJoin(o.cfg.OffloadDir, userID, sessionID)
}
