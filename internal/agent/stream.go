// Package agent 的流式事件消费引擎与执行生命周期观测。
//
// 职责：
//   - Run() 创建每轮隔离的 RunMetrics 与 Eino Runner，驱动流式执行并归结 Result；
//   - runSession 封装单次运行的局部消费状态（正文缓冲、工具计时、结果集），
//     将 Eino ADK 事件流翻译为 SSE 展示事件、完整 Transcript 与摘要检查点；
//   - executionCallbacks 订阅 Eino 模型/工具生命周期写结构化日志，与 SSE 推送解耦。
//
// 关键不变量：
//   - 子代理内部事件（len(event.RunPath) > 1）必须丢弃并显式 Close 流，防止混入主正文或泄漏流资源；
//   - 流式分片必须用 schema.ConcatMessages 合并，不可直接拼字符串（否则丢失跨片工具参数与 Usage）；
//   - 工具调用或模型重试后必须发送 Reset 撤回临时正文，保证前端展示与最终持久化内容一致。
package agent

import (
	"context"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/summarization"
	"github.com/cloudwego/eino/callbacks"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
	template "github.com/cloudwego/eino/utils/callbacks"
	"go.uber.org/zap"

	"mentorly/internal/utils"
	logutil "mentorly/internal/utils/log"
)

// Run 驱动一次 TutorAgent 流式执行；消息持久化与 done 事件发送由上层 Service 负责。
func (a *Agent) Run(ctx context.Context, rc *RunContext, sink Emitter) Result {
	started := time.Now()
	logger := logutil.FromContext(ctx, a.log)
	ctx = logutil.WithContext(ctx, logger)

	// 单轮用量统计对象挂在 ctx 上，主代理、子代理与摘要模型自动共享同一汇总器。
	metrics := &runMetrics{}
	ctx = context.WithValue(ctx, metricsContextKey{}, metrics)

	if rc == nil {
		return a.finish(ctx, sink, Result{}, fmt.Errorf("运行上下文为空"), started, metrics)
	}
	if !a.Enabled() {
		return a.finish(ctx, sink, Result{}, ErrUnavailable, started, metrics)
	}

	ctx = withPrincipal(ctx, rc.principal)
	runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: a.agent, EnableStreaming: true})

	session := &runSession{
		logger:     logger,
		sink:       sink,
		toolStarts: make(map[string]time.Time),
	}
	res := session.consume(ctx, runner.Run(ctx, rc.Messages, adk.WithCallbacks(executionCallbacks(logger))))
	return a.finish(ctx, sink, res, res.runErr, started, metrics)
}

// runSession 仅存活于单次 Run 调用内（无并发读写），收敛事件消费所需的全部中间态。
type runSession struct {
	logger     *zap.Logger
	sink       Emitter
	res        Result
	buf        strings.Builder      // 仅累计当前最终答复正文；触发工具调用或重试时清空。
	toolStarts map[string]time.Time // 按 CallID 计时，避免同名工具并行或多次调用互相覆盖。
}

// reset 清空当前暂存正文并通知前端撤回，用于工具决策与模型重试场景。
func (s *runSession) reset() error {
	s.res.Message = nil
	if s.buf.Len() == 0 {
		return nil
	}
	s.buf.Reset()
	return emit(s.sink, Event{Type: EventMessage, Data: MessageData{Reset: true}})
}

// consume 持续消费 Eino 事件迭代器，直到自然结束、上下文取消或下游写入失败。
func (s *runSession) consume(ctx context.Context, iter *adk.AsyncIterator[*adk.AgentEvent]) Result {
	defer func() {
		if s.res.Message == nil {
			s.res.Message = schema.AssistantMessage("", nil)
		}
		s.res.Message.Content = strings.TrimSpace(s.buf.String())
	}()

	for {
		if ctx.Err() != nil {
			return s.res
		}
		event, ok := iter.Next()
		if !ok {
			return s.res
		}
		if event.Err != nil {
			// WillRetryError 表示框架将按 ModelRetryConfig 重试，并非本轮最终失败。
			var retry *adk.WillRetryError
			if errors.As(event.Err, &retry) {
				s.logger.Warn("[模型重试]", logutil.Content("原因", retry.Error()))
				if err := s.reset(); err != nil {
					s.res.runErr = err
					return s.res
				}
				continue
			}
			s.res.runErr = event.Err
			return s.res
		}

		if event.Action != nil {
			// 摘要中间件通过 CustomizedAction 派发阶段事件，不属于前端展示正文。
			if action, ok := event.Action.CustomizedAction.(*summarization.CustomizedAction); ok {
				s.handleSummaryAction(action)
			}
		}

		if event.Output == nil || event.Output.MessageOutput == nil {
			continue
		}
		mv := event.Output.MessageOutput

		// 隔离 SubAgent 内部事件（RunPath 深度 > 1），显式关闭未消费的流防止资源泄漏。
		if len(event.RunPath) > 1 {
			if mv.MessageStream != nil {
				mv.MessageStream.Close()
			}
			continue
		}

		switch {
		case mv.Role == schema.Tool:
			if err := s.handleToolOutput(mv); err != nil {
				s.res.runErr = err
				return s.res
			}
		case mv.Role != "" && mv.Role != schema.Assistant:
			continue
		case mv.IsStreaming && mv.MessageStream != nil:
			if err := s.consumeStream(ctx, mv.MessageStream); err != nil {
				s.res.runErr = err
				return s.res
			}
		case mv.Message != nil:
			if err := s.handleAssistantMessage(ctx, mv.Message, false); err != nil {
				s.res.runErr = err
				return s.res
			}
		}
	}
}

// handleSummaryAction 仅在 AfterSummarize 阶段捕获检查点；失败的摘要不产生落库候选。
func (s *runSession) handleSummaryAction(action *summarization.CustomizedAction) {
	switch action.Type {
	case summarization.ActionTypeBeforeSummarize:
		s.logger.Info("[上下文压缩]")
	case summarization.ActionTypeGenerateSummary:
		if g := action.GenerateSummary; g != nil {
			if g.ModelResponse != nil {
				s.logger.Info("[压缩摘要]", logutil.Content("内容", g.ModelResponse.Content))
			}
			if err := g.GetError(); err != nil {
				s.logger.Warn("[压缩失败]", logutil.Content("错误", err.Error()))
			}
		}
	case summarization.ActionTypeAfterSummarize:
		s.logger.Info("[上下文压缩结束]")
		if action.After == nil {
			return
		}
		// System 提示词每次由 Agent 静态装配，检查点只保存非 System 的可恢复消息。
		compacted := make([]*schema.Message, 0, len(action.After.Messages))
		for _, msg := range action.After.Messages {
			if msg != nil && msg.Role != schema.System {
				compacted = append(compacted, msg)
			}
		}
		if len(compacted) > 0 {
			// CoveredTranscriptCount 锁定此刻已消费的原始 Transcript 长度，后续工具记录不归入该检查点。
			s.res.Compaction = &CompactionResult{
				Messages:               compacted,
				CoveredTranscriptCount: len(s.res.Transcript),
			}
		}
	}
}

// handleToolOutput 统一读取非流式/流式工具结果，记入完整 Transcript 并向前端推送截断预览。
func (s *runSession) handleToolOutput(mv *adk.MessageVariant) error {
	msg, err := mv.GetMessage()
	if err != nil || msg == nil {
		return err
	}
	if msg.ToolName == "" {
		msg.ToolName = mv.ToolName
	}
	var elapsed int64
	if t, ok := s.toolStarts[msg.ToolCallID]; ok {
		elapsed = time.Since(t).Milliseconds()
	}
	s.logger.Info("[工具返回："+msg.ToolName+"]", logutil.Content("结果", msg.Content))

	// 持久化保留工具原文，SSE 仅发 400 字符预览，避免大输出撑爆前端事件流。
	s.res.Transcript = append(s.res.Transcript, msg)
	if err := emit(s.sink, Event{Type: EventToolEnd, Data: ToolData{
		Name: msg.ToolName, CallID: msg.ToolCallID, Result: utils.Truncate(msg.Content, 400), ElapsedMS: elapsed,
	}}); err != nil {
		return err
	}
	return s.reset()
}

// handleAssistantMessage 区分“工具调用决策”与“最终答复”；alreadyStreamed 避免正文重复推送。
func (s *runSession) handleAssistantMessage(ctx context.Context, msg *schema.Message, alreadyStreamed bool) error {
	logAssistant(ctx, msg, false)
	if len(msg.ToolCalls) > 0 {
		s.res.Transcript = append(s.res.Transcript, msg)
		// 等待完整消息合并后再发送 tool_start，避免流式 JSON 参数碎片触发重复事件。
		for _, tc := range msg.ToolCalls {
			if tc.Function.Name == "" {
				continue
			}
			s.res.ToolCalls = append(s.res.ToolCalls, tc.Function.Name)
			s.toolStarts[tc.ID] = time.Now()
			if err := emit(s.sink, Event{Type: EventToolStart, Data: ToolData{
				Name: tc.Function.Name, CallID: tc.ID, Args: utils.Truncate(tc.Function.Arguments, 300),
			}}); err != nil {
				return err
			}
		}
		return s.reset()
	}
	// 保留完整原生消息，使 Usage、FinishReason 与多模态输出字段不丢失。
	s.res.Message = msg
	if !alreadyStreamed && msg.Content != "" {
		s.buf.WriteString(msg.Content)
		return emit(s.sink, Event{Type: EventMessage, Data: MessageData{Text: msg.Content}})
	}
	return nil
}

// consumeStream 边向前端推送增量正文边收集原生分片，流结束时统一用 ConcatMessages 合并。
func (s *runSession) consumeStream(ctx context.Context, sr *schema.StreamReader[*schema.Message]) error {
	defer sr.Close()
	var chunks []*schema.Message
	sawToolCall, rejected := false, false
	defer func() {
		// 若中途断连或超时，仍尽力保留已生成的原生消息字段；被重试拒绝的输出禁止落入最终结果。
		if !rejected && !sawToolCall && len(chunks) > 0 && s.res.Message == nil {
			s.res.Message, _ = schema.ConcatMessages(chunks)
			logAssistant(ctx, s.res.Message, true)
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
				return s.handleAssistantMessage(ctx, msg, true)
			}
			var retry *adk.WillRetryError
			if errors.As(err, &retry) && ctx.Err() == nil {
				rejected = true
				s.logger.Warn("[模型重试]", logutil.Content("原因", retry.Error()))
				return s.reset()
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
			// 一旦分片出现工具调用，说明此前流出的正文属于思考前导语，立即通知前端撤回。
			sawToolCall = true
			if err := s.reset(); err != nil {
				return err
			}
			continue
		}
		if chunk.Content != "" {
			s.buf.WriteString(chunk.Content)
			if err := emit(s.sink, Event{Type: EventMessage, Data: MessageData{Text: chunk.Content}}); err != nil {
				return err
			}
		}
	}
}

// finish 统一收敛运行状态、记录聚合指标并按需发送 error 事件；done 事件由 Service 落库后发送。
func (a *Agent) finish(ctx context.Context, sink Emitter, res Result, runErr error, started time.Time, metrics *runMetrics) Result {
	res.Elapsed = time.Since(started)
	if res.Message == nil {
		res.Message = schema.AssistantMessage("", nil)
	}
	if runErr == nil && ctx.Err() == nil && strings.TrimSpace(res.Message.Content) == "" {
		runErr = errEmptyAgentOutput
	}

	res.Status, res.Message.Content = resolveStatus(res.Message.Content, runErr, ctx)
	summary := metrics.SummaryFields(res.Elapsed)
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

// executionCallbacks 订阅 Eino 模型和工具调用生命周期，独立于前端 SSE 事件流。
func executionCallbacks(logger *zap.Logger) callbacks.Handler {
	return template.NewHandlerHelper().
		ChatModel(&template.ModelCallbackHandler{
			OnStart: func(ctx context.Context, _ *callbacks.RunInfo, _ *model.CallbackInput) context.Context {
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

// logAssistant 记录公开正文与工具参数；思考内容仅记录字符数，不落盘原始思考正文。
func logAssistant(ctx context.Context, msg *schema.Message, partial bool) {
	if msg == nil {
		return
	}
	logger := logutil.FromContext(ctx, nil)
	if msg.ResponseMeta != nil || msg.ReasoningContent != "" {
		logger.Info("[模型响应统计]", usageLogFields(msg, 0)...)
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
