package agent

import (
	"context"
	"errors"
	"fmt"
	"io"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/summarization"
	"github.com/cloudwego/eino/callbacks"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
	template "github.com/cloudwego/eino/utils/callbacks"
	"go.uber.org/zap"

	logutil "mentorly/internal/utils/log"
)

// ---------- SSE 事件与执行结果协议 ----------

// SSE 事件类型与本轮执行终态常量（与前端协议及数据库状态一致）。
const (
	EventMessage   = "message"
	EventToolStart = "tool_start"
	EventToolEnd   = "tool_end"
	EventError     = "error"
	EventDone      = "done"

	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCancelled = "cancelled"
)

// Event 是一条待编码为 SSE 帧的业务事件。
type Event struct {
	Type string
	Data any
}

// MessageData 承载流式正文分片；Reset=true 通知前端清空此前过渡文本。
type MessageData struct {
	Text  string `json:"text"`
	Reset bool   `json:"reset,omitempty"`
}

// ToolData 承载 tool_start / tool_end 事件的工具调用摘要与耗时。
type ToolData struct {
	Name      string `json:"name"`
	CallID    string `json:"call_id,omitempty"`
	Args      string `json:"args,omitempty"`
	Result    string `json:"result,omitempty"`
	ElapsedMS int64  `json:"elapsed_ms,omitempty"`
}

// ErrorData 承载面向用户的脱敏错误信息。
type ErrorData struct {
	Message   string `json:"message"`
	Retryable bool   `json:"retryable,omitempty"`
}

// DoneData 承载本轮落库后的终态汇总信息（由 Service 发送）。
type DoneData struct {
	MessageID uint64   `json:"message_id"`
	Status    string   `json:"status"`
	ElapsedMS int64    `json:"elapsed_ms"`
	ToolCalls []string `json:"tool_calls,omitempty"`
}

// Emitter 接收业务事件；返回 error 时停止执行以节省算力。
type Emitter func(Event) error

// CompactionResult 记录本轮 Eino summarization 中间件产出的最新检查点。
type CompactionResult struct {
	Messages              []*schema.Message
	FoldedTranscriptCount int
}

// Result 是一轮 Agent 执行的最终结果，交由 Service 落库并发送 done 事件。
type Result struct {
	Message    *schema.Message
	Status     string
	MessageID  uint64
	ToolCalls  []string
	Transcript []*schema.Message
	Compaction *CompactionResult
	Elapsed    time.Duration
	runErr     error
}

var (
	errEmptyAgentOutput = errors.New("Agent 未返回最终结果")
	errOutputTruncated  = errors.New("模型输出达到长度上限被截断")
	errNoPrincipal      = errors.New("runtime: 缺少已认证用户上下文")
)

// ---------- 运行时身份上下文 ----------

// runPrincipal 是一次运行的身份与目录边界，仅通过 context 传递，绝不信任模型参数。
type runPrincipal struct {
	UserID         string
	ConversationID string
	Workspace      string
}

// principalKey 是 context.WithValue 专用的私有键，避免与其他包冲突。
type principalKey struct{}

// withPrincipal 将当前请求的身份与目录边界写入 context。
func withPrincipal(ctx context.Context, p *runPrincipal) context.Context {
	return context.WithValue(ctx, principalKey{}, p)
}

// principalFrom 从 context 中读取运行身份；缺失或 UserID 为空时返回 false。
func principalFrom(ctx context.Context) (*runPrincipal, bool) {
	p, ok := ctx.Value(principalKey{}).(*runPrincipal)
	if !ok || p == nil || strings.TrimSpace(p.UserID) == "" {
		return nil, false
	}
	return p, true
}

// mustPrincipal 读取运行身份，缺失时返回致命错误 errNoPrincipal。
func mustPrincipal(ctx context.Context) (*runPrincipal, error) {
	p, ok := principalFrom(ctx)
	if !ok {
		return nil, errNoPrincipal
	}
	return p, nil
}

// PrincipalIDs 提取当前运行上下文的 (userID, conversationID)，供外部工具包做归属校验。
func PrincipalIDs(ctx context.Context) (userID, conversationID string, err error) {
	p, err := mustPrincipal(ctx)
	if err != nil {
		return "", "", err
	}
	return p.UserID, p.ConversationID, nil
}

// WorkspaceDir 提取当前运行上下文的会话工作区路径，供外部命令执行工具使用。
func WorkspaceDir(ctx context.Context) (string, error) {
	p, err := mustPrincipal(ctx)
	if err != nil {
		return "", err
	}
	return p.Workspace, nil
}

// ---------- 主执行流 ----------

// Run 驱动一次 TutorAgent 流式执行；持久化和 done 事件由 Service 负责。
func (a *Agent) Run(ctx context.Context, rc *RunContext, sink Emitter) Result {
	started := time.Now()
	ctx = logutil.WithContext(ctx, logutil.FromContext(ctx, a.log))

	if rc == nil {
		return a.finish(ctx, sink, Result{}, fmt.Errorf("运行上下文为空"), started, nil)
	}
	if !a.Enabled() {
		return a.finish(ctx, sink, Result{}, ErrUnavailable, started, nil)
	}

	ctx = withPrincipal(ctx, rc.principal)
	runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: a.agent, EnableStreaming: true})
	metrics := &runMetrics{}
	res := a.consume(ctx, runner, rc, sink, metrics)
	return a.finish(ctx, sink, res, res.runErr, started, metrics)
}

// consume 消费 Eino Runner 事件流：转发文本分片与工具状态、处理重试重置并捕获压缩检查点。
func (a *Agent) consume(ctx context.Context, runner *adk.Runner, rc *RunContext, sink Emitter, metrics *runMetrics) (res Result) {
	logger := logutil.FromContext(ctx, a.log)
	iter := runner.Run(ctx, rc.Messages, adk.WithCallbacks(executionCallbacks(logger, metrics)))

	var buf strings.Builder
	defer func() {
		if res.Message == nil {
			res.Message = schema.AssistantMessage("", nil)
		}
		res.Message.Content = strings.TrimSpace(buf.String())
	}()

	toolStarts := make(map[string]time.Time)
	// 模型调用工具前的过渡语或被拒绝重试的半截输出不属于最终回答，需清空。
	reset := func() error {
		res.Message = nil
		if buf.Len() == 0 {
			return nil
		}
		buf.Reset()
		return emit(sink, Event{Type: EventMessage, Data: MessageData{Reset: true}})
	}

	for {
		if ctx.Err() != nil {
			return res
		}
		event, ok := iter.Next()
		if !ok {
			return res
		}
		if event.Err != nil {
			var retry *adk.WillRetryError
			if errors.As(event.Err, &retry) {
				logger.Warn("[模型重试]", logutil.Content("原因", retry.Error()))
				if err := reset(); err != nil {
					res.runErr = err
					return res
				}
				continue
			}
			res.runErr = event.Err
			return res
		}

		// 捕获 summarization 中间件发出的压缩检查点。
		if event.Action != nil {
			if action, ok := event.Action.CustomizedAction.(*summarization.CustomizedAction); ok {
				handleSummaryAction(logger, action, &res)
			}
		}

		if event.Output == nil || event.Output.MessageOutput == nil {
			continue
		}
		mv := event.Output.MessageOutput

		if mv.Role == schema.Tool {
			if err := handleToolOutput(ctx, logger, mv, sink, &res, toolStarts, reset); err != nil {
				res.runErr = err
				return res
			}
			continue
		}
		if mv.Role != "" && mv.Role != schema.Assistant {
			continue
		}
		if mv.IsStreaming && mv.MessageStream != nil {
			if err := consumeStream(ctx, mv.MessageStream, &buf, sink, &res, toolStarts, reset, metrics); err != nil {
				res.runErr = err
				return res
			}
			continue
		}
		if mv.Message != nil {
			if err := handleAssistantMessage(ctx, mv.Message, false, &buf, sink, &res, toolStarts, reset, metrics); err != nil {
				res.runErr = err
				return res
			}
		}
	}
}

// handleSummaryAction 记录上下文压缩日志，并在压缩完成后保存去除了 System 的检查点消息。
func handleSummaryAction(logger *zap.Logger, action *summarization.CustomizedAction, res *Result) {
	switch action.Type {
	case summarization.ActionTypeBeforeSummarize:
		logger.Info("[上下文压缩]")
	case summarization.ActionTypeGenerateSummary:
		if g := action.GenerateSummary; g != nil {
			if g.ModelResponse != nil {
				logger.Info("[压缩摘要]", logutil.Content("内容", g.ModelResponse.Content))
			}
			if err := g.GetError(); err != nil {
				logger.Warn("[压缩失败]", logutil.Content("错误", err.Error()))
			}
		}
	case summarization.ActionTypeAfterSummarize:
		logger.Info("[上下文压缩结束]")
		if action.After != nil {
			if compacted := stripSystemMessages(action.After.Messages); len(compacted) > 0 {
				res.Compaction = &CompactionResult{Messages: compacted, FoldedTranscriptCount: len(res.Transcript)}
			}
		}
	}
}

// handleToolOutput 记录工具返回消息到 Transcript，向前端发送 tool_end 并重置正文缓冲。
func handleToolOutput(
	ctx context.Context,
	logger *zap.Logger,
	mv *adk.MessageVariant,
	sink Emitter,
	res *Result,
	toolStarts map[string]time.Time,
	reset func() error,
) error {
	msg, err := mv.GetMessage()
	if err != nil || msg == nil {
		return err
	}
	if msg.ToolName == "" {
		msg.ToolName = mv.ToolName
	}
	var elapsed int64
	if t, ok := toolStarts[msg.ToolCallID]; ok {
		elapsed = time.Since(t).Milliseconds()
	}
	logger.Info("[工具返回："+msg.ToolName+"]", logutil.Content("结果", msg.Content))
	res.Transcript = append(res.Transcript, msg)

	if err := emit(sink, Event{Type: EventToolEnd, Data: ToolData{
		Name: msg.ToolName, CallID: msg.ToolCallID, Result: truncate(msg.Content, 400), ElapsedMS: elapsed,
	}}); err != nil {
		return err
	}
	return reset()
}

// handleAssistantMessage 统一收尾流式与非流式助手消息：记统计、处理工具调用或最终文本。
func handleAssistantMessage(
	ctx context.Context,
	msg *schema.Message,
	alreadyStreamed bool,
	buf *strings.Builder,
	sink Emitter,
	res *Result,
	toolStarts map[string]time.Time,
	reset func() error,
	metrics *runMetrics,
) error {
	logAssistant(ctx, msg, false, metrics.recordModelOutput(msg))
	if len(msg.ToolCalls) > 0 {
		res.Transcript = append(res.Transcript, msg)
		if err := startTools(sink, res, toolStarts, msg.ToolCalls); err != nil {
			return err
		}
		if !alreadyStreamed {
			return reset()
		}
		return nil
	}
	res.Message = msg
	if !alreadyStreamed && msg.Content != "" {
		buf.WriteString(msg.Content)
		return emit(sink, Event{Type: EventMessage, Data: MessageData{Text: msg.Content}})
	}
	return nil
}

// consumeStream 逐帧消费模型流式输出，实时推送文本分片并在 EOF 时合并为完整 schema.Message。
func consumeStream(
	ctx context.Context,
	sr *schema.StreamReader[*schema.Message],
	buf *strings.Builder,
	sink Emitter,
	res *Result,
	toolStarts map[string]time.Time,
	reset func() error,
	metrics *runMetrics,
) error {
	defer sr.Close()
	var chunks []*schema.Message
	sawToolCall, rejected := false, false
	// 中途断连或取消时，把已收到的分片合入 res.Message 并记为中断输出。
	defer func() {
		if !rejected && !sawToolCall && len(chunks) > 0 && res.Message == nil {
			res.Message, _ = schema.ConcatMessages(chunks)
			logAssistant(ctx, res.Message, true, metrics.recordModelOutput(res.Message))
		}
	}()

	for {
		chunk, err := sr.Recv()
		if err != nil {
			if errors.Is(err, io.EOF) {
				if len(chunks) == 0 {
					return nil
				}
				msg, err := schema.ConcatMessages(chunks)
				if err != nil {
					return fmt.Errorf("合并模型消息失败: %w", err)
				}
				return handleAssistantMessage(ctx, msg, true, buf, sink, res, toolStarts, reset, metrics)
			}
			var retry *adk.WillRetryError
			if errors.As(err, &retry) && ctx.Err() == nil {
				rejected = true
				logutil.FromContext(ctx, nil).Warn("[模型重试]", logutil.Content("原因", retry.Error()))
				return reset()
			}
			if ctxErr := ctx.Err(); ctxErr != nil {
				return ctxErr
			}
			return err
		}
		if chunk == nil {
			continue
		}
		chunks = append(chunks, chunk)

		if len(chunk.ToolCalls) > 0 {
			sawToolCall = true
			if err := reset(); err != nil {
				return err
			}
			continue
		}
		if chunk.Content != "" {
			buf.WriteString(chunk.Content)
			if err := emit(sink, Event{Type: EventMessage, Data: MessageData{Text: chunk.Content}}); err != nil {
				return err
			}
		}
	}
}

// startTools 记录工具开始时间并向前端推送 tool_start 事件。
func startTools(sink Emitter, res *Result, starts map[string]time.Time, calls []schema.ToolCall) error {
	for _, tc := range calls {
		if tc.Function.Name == "" {
			continue
		}
		res.ToolCalls = append(res.ToolCalls, tc.Function.Name)
		starts[tc.ID] = time.Now()
		if err := emit(sink, Event{Type: EventToolStart, Data: ToolData{
			Name: tc.Function.Name, CallID: tc.ID, Args: truncate(tc.Function.Arguments, 300),
		}}); err != nil {
			return err
		}
	}
	return nil
}

// finish 汇总本轮耗时、终态与统计日志，失败时推送面向用户的 error 事件。
func (a *Agent) finish(ctx context.Context, sink Emitter, res Result, runErr error, started time.Time, metrics *runMetrics) Result {
	res.Elapsed = time.Since(started)
	if res.Message == nil {
		res.Message = schema.AssistantMessage("", nil)
	}
	if runErr == nil && ctx.Err() == nil && strings.TrimSpace(res.Message.Content) == "" {
		runErr = errEmptyAgentOutput
	}

	res.Status, res.Message.Content = resolveStatus(res.Message.Content, runErr, ctx)
	summary := metrics.summaryFields(res.Elapsed)
	logger := logutil.FromContext(ctx, a.log)

	if runErr != nil {
		logger.Warn("[Agent 执行失败]", append([]zap.Field{logutil.Content("错误", runErr.Error())}, summary...)...)
		_ = emit(sink, Event{Type: EventError, Data: ErrorData{Message: userFacingError(runErr), Retryable: isTransient(runErr)}})
	}
	if ctx.Err() != nil {
		logger.Warn("[Agent 已停止]", append([]zap.Field{logutil.Content("原因", ctx.Err().Error())}, summary...)...)
	} else if runErr == nil {
		logger.Info("[Agent 执行结束]", summary...)
	}
	return res
}

// ---------- 状态与错误映射 ----------

// resolveStatus 优先判定 ctx 取消，避免客户端断连时流正常 EOF 被误标为 completed。
func resolveStatus(answer string, runErr error, ctx context.Context) (status, content string) {
	if errors.Is(runErr, context.Canceled) || errors.Is(runErr, context.DeadlineExceeded) || ctx.Err() != nil {
		if strings.TrimSpace(answer) == "" {
			answer = "[本轮生成已停止]"
		}
		return StatusCancelled, answer
	}
	if runErr == nil {
		return StatusCompleted, answer
	}
	if strings.TrimSpace(answer) == "" {
		answer = userFacingError(runErr)
	}
	return StatusFailed, answer
}

// userFacingError 将内部错误映射为对学生友好的脱敏文案，不暴露栈信息、地址或端口。
func userFacingError(err error) string {
	if err == nil {
		return ""
	}
	msg := err.Error()
	switch {
	case errors.Is(err, context.DeadlineExceeded):
		return "本轮生成超时，请重试"
	case errors.Is(err, context.Canceled):
		return "生成已取消"
	case errors.Is(err, ErrUnavailable):
		return "对话能力未启用"
	case errors.Is(err, errOutputTruncated):
		return "模型单次思考或输出超过长度上限，请缩小单次需求范围或重试"
	case errors.Is(err, errEmptyAgentOutput):
		return "Agent 未返回最终结果，请检查工作区文件或重试"
	case strings.Contains(msg, "failed to unmarshal arguments"):
		return "工具参数格式有误，请重试（通常是内容过长或含特殊字符）"
	case strings.Contains(msg, "failed to stream tool call"), strings.Contains(msg, "failed to invoke tool"):
		return "工具调用失败，请重试"
	case isTransient(err):
		return "上游服务暂时不可用，请重试"
	default:
		return "生成失败，请稍后重试"
	}
}

// isTransient 判断错误是否属于可重试的上游瞬时故障（限流、5xx、超时、断连）。
func isTransient(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	for _, kw := range []string{
		"429", "500", "502", "503", "504",
		"timeout", "timed out", "deadline",
		"connection reset", "connection refused", "broken pipe",
		"temporarily unavailable", "overloaded", "rate limit", "eof",
	} {
		if strings.Contains(msg, kw) {
			return true
		}
	}
	return false
}

// emit 安全调用事件发射器；sink 为 nil（如单测场景）时静默忽略。
func emit(e Emitter, ev Event) error {
	if e == nil {
		return nil
	}
	return e(ev)
}

// truncate 按 Unicode 字符数截断字符串，避免截断多字节中文字符。
func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n]) + "…"
}

// stripSystemMessages 过滤消息列表中的 system 消息，确保压缩检查点落库不含系统提示词。
func stripSystemMessages(msgs []*schema.Message) []*schema.Message {
	out := make([]*schema.Message, 0, len(msgs))
	for _, m := range msgs {
		if m != nil && m.Role != schema.System {
			out = append(out, m)
		}
	}
	return out
}

// finishReasonOf 读取模型响应的 finish_reason（如 stop、tool_calls、length）。
func finishReasonOf(msg *schema.Message) string {
	if msg == nil || msg.ResponseMeta == nil {
		return ""
	}
	return strings.TrimSpace(msg.ResponseMeta.FinishReason)
}

// ---------- 指标与可观测日志 ----------

// runMetrics 跨 runner goroutine 与消费 goroutine 统计本轮模型调用次数、耗时与 Token 用量。
type runMetrics struct {
	mu               sync.Mutex
	modelCalls       int
	lastModelStart   time.Time
	promptTokens     int
	completionTokens int
	reasoningTokens  int
	totalTokens      int
}

// startModelCall 在 ChatModel OnStart 回调中累加调用次数并记录本次起始时间。
func (m *runMetrics) startModelCall() {
	if m == nil {
		return
	}
	m.mu.Lock()
	m.modelCalls++
	m.lastModelStart = time.Now()
	m.mu.Unlock()
}

// recordModelOutput 累计本轮 Token 用量并返回当次模型调用耗时（毫秒）。
func (m *runMetrics) recordModelOutput(msg *schema.Message) int64 {
	if m == nil {
		return 0
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	var elapsed int64
	if !m.lastModelStart.IsZero() {
		elapsed = time.Since(m.lastModelStart).Milliseconds()
	}
	if msg != nil && msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil {
		u := msg.ResponseMeta.Usage
		m.promptTokens += u.PromptTokens
		m.completionTokens += u.CompletionTokens
		m.reasoningTokens += u.CompletionTokensDetails.ReasoningTokens
		m.totalTokens += u.TotalTokens
	}
	return elapsed
}

// summaryFields 导出本轮结束日志所需的总耗时、调用次数与 Token 汇总字段。
func (m *runMetrics) summaryFields(elapsed time.Duration) []zap.Field {
	fields := []zap.Field{zap.Int64("elapsed_ms", elapsed.Milliseconds())}
	if m == nil {
		return fields
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	return append(fields,
		zap.Int("model_calls", m.modelCalls),
		zap.Int("prompt_tokens", m.promptTokens),
		zap.Int("completion_tokens", m.completionTokens),
		zap.Int("reasoning_tokens", m.reasoningTokens),
		zap.Int("total_tokens", m.totalTokens),
	)
}

// executionCallbacks 构造单次运行的 Eino Callbacks：通过 adk.WithCallbacks 按次注入（而非共享中间件），
// 以隔离每次并发请求的 logger 与 runMetrics 状态。
func executionCallbacks(logger *zap.Logger, metrics *runMetrics) callbacks.Handler {
	return template.NewHandlerHelper().
		ChatModel(&template.ModelCallbackHandler{
			OnStart: func(ctx context.Context, _ *callbacks.RunInfo, _ *model.CallbackInput) context.Context {
				metrics.startModelCall()
				logger.Info("[模型调用]")
				return ctx
			},
			OnError: func(ctx context.Context, _ *callbacks.RunInfo, err error) context.Context {
				logger.Warn("[模型错误]", logutil.Content("错误", err.Error()))
				return ctx
			},
		}).Tool(&template.ToolCallbackHandler{
		OnStart: func(ctx context.Context, info *callbacks.RunInfo, input *tool.CallbackInput) context.Context {
			if input != nil {
				logger.Info("[工具执行：" + info.Name + "]")
			}
			return ctx
		},
		OnError: func(ctx context.Context, info *callbacks.RunInfo, err error) context.Context {
			logger.Warn("[工具错误："+info.Name+"]", logutil.Content("错误", err.Error()))
			return ctx
		},
	}).Handler()
}

// usageLogFields 提取模型响应的用量与推理长度（不记录 ReasoningContent 原文）。
func usageLogFields(msg *schema.Message, elapsedMS int64) []zap.Field {
	reason := finishReasonOf(msg)
	if reason == "" {
		reason = "未提供"
	}
	fields := []zap.Field{zap.String("finish_reason", reason)}
	if elapsedMS > 0 {
		fields = append(fields, zap.Int64("model_elapsed_ms", elapsedMS))
	}
	if msg == nil {
		return fields
	}
	fields = append(fields,
		zap.Int("reasoning_chars", utf8.RuneCountInString(msg.ReasoningContent)),
		zap.Int("content_chars", utf8.RuneCountInString(msg.Content)),
		zap.Int("tool_calls", len(msg.ToolCalls)),
	)
	if msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil {
		u := msg.ResponseMeta.Usage
		fields = append(fields,
			zap.Int("prompt_tokens", u.PromptTokens),
			zap.Int("completion_tokens", u.CompletionTokens),
			zap.Int("reasoning_tokens", u.CompletionTokensDetails.ReasoningTokens),
			zap.Int("total_tokens", u.TotalTokens),
		)
	}
	return fields
}

// logAssistant 输出助手响应的统计指标、正文（或中断输出）及工具调用参数日志。
func logAssistant(ctx context.Context, msg *schema.Message, partial bool, elapsedMS int64) {
	if msg == nil {
		return
	}
	logger := logutil.FromContext(ctx, nil)
	if msg.ResponseMeta != nil || msg.ReasoningContent != "" || elapsedMS > 0 {
		logger.Info("[模型响应统计]", usageLogFields(msg, elapsedMS)...)
	}
	if msg.Content != "" {
		stage := "[Agent 输出]"
		if partial {
			stage = "[Agent 输出中断]"
		}
		logger.Info(stage, logutil.Content("内容", msg.Content))
	}
	for _, call := range msg.ToolCalls {
		logger.Info("[Agent 工具调用："+call.Function.Name+"]", logutil.Content("参数", call.Function.Arguments))
	}
}
