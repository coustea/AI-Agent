package tutor

import (
	"context"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"
)

// Result 是一轮运行的最终结果。
type Result struct {
	// Answer 最终回答（最后一次 reset 之后累积的文本）
	Answer string
	// Status completed / failed / cancelled
	Status string
	// MessageID 落库后的 assistant 消息 ID
	MessageID uint64
	// Usage 模型返回的真实 token 用量
	Usage *schema.TokenUsage
	// ToolCalls 本轮调用过的工具名
	ToolCalls []string
	// Elapsed 本轮耗时
	Elapsed time.Duration
	// runErr 是执行过程中记录的错误（含工具调用失败），
	// 用于终态判定，不对外暴露。
	runErr error
}

// Runtime 执行 TutorAgent 并把 Eino 原生 AgentEvent 转换成业务事件。
//
// 它不实现任何 Agent 决策：ReAct 循环、工具调度、上下文压缩
// 全部由 Eino ADK 与其官方 Middleware 完成。
// 这里只做三件事：
//
//  1. 驱动 Runner 并消费事件流；
//  2. 把 AgentEvent 翻译成面向前端的业务事件；
//  3. 收口落库。
type Runtime struct {
	agent *Agent
	store ConversationStore
	log   *zap.Logger
}

// RuntimeDeps 是 Runtime 的装配参数。
type RuntimeDeps struct {
	Agent *Agent
	Store ConversationStore
	Log   *zap.Logger
}

// NewRuntime 构造 Runtime。
func NewRuntime(d RuntimeDeps) *Runtime {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	return &Runtime{agent: d.Agent, store: d.Store, log: log}
}

// Run 执行一轮对话。
//
// sink 接收业务事件；即使客户端断开，也会用 WithoutCancel 落库。
// 返回值是落库后的真实结果，供传输层拼 done 帧。
func (r *Runtime) Run(ctx context.Context, rc *RunContext, sink Emitter) Result {
	started := time.Now()

	if rc == nil {
		return r.finish(ctx, nil, sink, Result{}, fmt.Errorf("运行上下文为空"), started)
	}

	// 注入身份：所有 Capability 的工具都从这里取用户 ID。
	ctx = withRunContext(ctx, rc)

	runner, err := r.agent.Build(ctx, BuildSpec{
		Instruction: rc.Instruction,
		Sandbox:     rc.Sandbox,
	})
	if err != nil {
		return r.finish(ctx, rc, sink, Result{}, fmt.Errorf("构建 Agent 失败: %w", err), started)
	}

	res := r.consume(ctx, runner, rc, sink)
	return r.finish(ctx, rc, sink, res, res.runErr, started)
}

// consume 消费 Eino Runner 的事件流。
//
// 事件处理规则（对应 Eino 的 AgentEvent 结构）：
//   - MessageOutput.Role == tool：工具结果，记录工具名，内容不进回答；
//   - MessageOutput.Role == assistant 且流式：逐块读文本推给前端；
//   - 某个块携带 ToolCalls：说明模型要调工具，此前文本是过渡语，需要 reset；
//   - 末包 ResponseMeta.Usage：真实 token 用量；
//   - ctx 取消：立刻返回，由上层落库 cancelled。
func (r *Runtime) consume(ctx context.Context, runner *adk.Runner, rc *RunContext, sink Emitter) Result {
	res := Result{}

	iter := runner.Run(ctx, rc.Messages)

	var buf strings.Builder
	toolStarts := make(map[string]time.Time)
	toolArgs := make(map[string]string)

	// reset 清空已渲染内容：模型调用工具前的过渡语不属于最终回答。
	reset := func() error {
		if buf.Len() == 0 {
			return nil
		}
		buf.Reset()
		return emit(sink, Event{Type: EventMessage, Data: MessageData{Reset: true}})
	}

	for {
		// 先检查取消：客户端断开后不应继续消费事件。
		if err := ctx.Err(); err != nil {
			res.Answer = strings.TrimSpace(buf.String())
			return res
		}

		event, ok := iter.Next()
		if !ok {
			break
		}
		if event.Err != nil {
			res.Answer = strings.TrimSpace(buf.String())
			// 取消不算业务错误，由 resolveStatus 统一判定。
			if !errors.Is(event.Err, context.Canceled) && !errors.Is(event.Err, context.DeadlineExceeded) {
				r.log.Warn("Agent 执行返回错误",
					zap.Error(event.Err),
					zap.String("conversation_id", rc.Principal.ConversationID),
				)
				_ = emit(sink, Event{Type: EventError, Data: ErrorData{
					Message:   userFacingError(event.Err),
					Retryable: isTransient(event.Err),
				}})
				// 记录错误，供 finish 判定终态。
				// 否则工具调用失败会被误记为 completed——
				// 用户看到「完成」，实际什么都没生成。
				res.runErr = event.Err
			}
			return res
		}

		if event.Output == nil || event.Output.MessageOutput == nil {
			continue
		}

		mv := event.Output.MessageOutput

		// ---- 工具结果 ----
		if mv.Role == schema.Tool {
			name := mv.ToolName
			if name != "" {
				res.ToolCalls = append(res.ToolCalls, name)
			}
			callID := ""
			if mv.Message != nil {
				callID = mv.Message.ToolCallID
			}

			var elapsed int64
			if t, ok := toolStarts[callID]; ok {
				elapsed = time.Since(t).Milliseconds()
			}

			result := ""
			if mv.Message != nil {
				result = truncate(mv.Message.Content, 400)
			}

			_ = emit(sink, Event{Type: EventToolEnd, Data: ToolData{
				Name:      name,
				CallID:    callID,
				Result:    result,
				ElapsedMS: elapsed,
			}})
			// 工具执行后清空过渡语，让最终回答从干净状态开始。
			if err := reset(); err != nil {
				res.Answer = strings.TrimSpace(buf.String())
				return res
			}
			continue
		}

		// 只关心 assistant 输出
		if mv.Role != "" && mv.Role != schema.Assistant {
			continue
		}

		// ---- 流式 assistant ----
		if mv.IsStreaming && mv.MessageStream != nil {
			if err := r.consumeStream(ctx, mv.MessageStream, &buf, sink, &res, toolStarts, toolArgs, reset); err != nil {
				res.Answer = strings.TrimSpace(buf.String())
				return res
			}
			continue
		}

		if mv.Message == nil {
			continue
		}
		msg := mv.Message

		// 非流式消息携带工具调用：先 reset 过渡语
		if len(msg.ToolCalls) > 0 {
			for _, tc := range msg.ToolCalls {
				if tc.Function.Name == "" {
					continue
				}
				res.ToolCalls = append(res.ToolCalls, tc.Function.Name)
				toolStarts[tc.ID] = time.Now()
				toolArgs[tc.ID] = tc.Function.Arguments
				_ = emit(sink, Event{Type: EventToolStart, Data: ToolData{
					Name:   tc.Function.Name,
					CallID: tc.ID,
					Args:   truncate(tc.Function.Arguments, 300),
				}})
			}
			if err := reset(); err != nil {
				res.Answer = strings.TrimSpace(buf.String())
				return res
			}
			continue
		}

		if msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil {
			res.Usage = msg.ResponseMeta.Usage
		}

		if msg.Content == "" {
			continue
		}
		buf.WriteString(msg.Content)
		if err := emit(sink, Event{Type: EventMessage, Data: MessageData{Text: msg.Content}}); err != nil {
			res.Answer = strings.TrimSpace(buf.String())
			return res
		}
	}

	res.Answer = strings.TrimSpace(buf.String())
	return res
}

// consumeStream 消费一个流式消息。
func (r *Runtime) consumeStream(
	ctx context.Context,
	sr *schema.StreamReader[*schema.Message],
	buf *strings.Builder,
	sink Emitter,
	res *Result,
	toolStarts map[string]time.Time,
	toolArgs map[string]string,
	reset func() error,
) error {
	// 必须关闭，否则底层 goroutine 泄漏。
	defer sr.Close()

	for {
		chunk, err := sr.Recv()
		if err != nil {
			if errors.Is(err, io.EOF) {
				return nil
			}
			// ctx 取消时 Recv 会报错，交给上层按取消处理。
			if ctxErr := ctx.Err(); ctxErr != nil {
				return ctxErr
			}
			return err
		}
		if chunk == nil {
			continue
		}

		if chunk.ResponseMeta != nil && chunk.ResponseMeta.Usage != nil {
			res.Usage = chunk.ResponseMeta.Usage
		}

		// 工具调用：记录并 reset 过渡语
		if len(chunk.ToolCalls) > 0 {
			for _, tc := range chunk.ToolCalls {
				if tc.Function.Name == "" {
					continue
				}
				res.ToolCalls = append(res.ToolCalls, tc.Function.Name)
				toolStarts[tc.ID] = time.Now()
				toolArgs[tc.ID] = tc.Function.Arguments
				_ = emit(sink, Event{Type: EventToolStart, Data: ToolData{
					Name:   tc.Function.Name,
					CallID: tc.ID,
					Args:   truncate(tc.Function.Arguments, 300),
				}})
			}
			if err := reset(); err != nil {
				return err
			}
			continue
		}

		if chunk.Content == "" {
			continue
		}
		buf.WriteString(chunk.Content)
		if err := emit(sink, Event{Type: EventMessage, Data: MessageData{Text: chunk.Content}}); err != nil {
			return err
		}
	}
}

// finish 收口：判定终态、落库、发 done 事件。
func (r *Runtime) finish(ctx context.Context, rc *RunContext, sink Emitter, res Result, runErr error, started time.Time) Result {
	res.Elapsed = time.Since(started)

	status, content := resolveStatus(res.Answer, runErr, ctx)
	res.Status = status
	res.Answer = content

	if runErr != nil {
		r.log.Warn("本轮对话失败",
			zap.Error(runErr),
			zap.String("status", status),
		)
		// 失败时把可读信息推给前端；done 帧由传输层在 Run 返回后发送。
		_ = emit(sink, Event{Type: EventError, Data: ErrorData{
			Message:   userFacingError(runErr),
			Retryable: isTransient(runErr),
		}})
	}

	// 即使 ctx 已取消也要落库：用 WithoutCancel 断开取消信号传播。
	if rc != nil {
		saveCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 10*time.Second)
		defer cancel()

		msg := &Message{
			Role:    RoleAssistant,
			Content: content,
			Status:  status,
		}
		if res.Usage != nil {
			msg.Tokens = res.Usage.CompletionTokens
		}
		if err := r.store.CreateMessage(saveCtx, rc.Principal.ConversationID, msg); err != nil {
			r.log.Error("落库 assistant 消息失败",
				zap.Error(err),
				zap.String("status", status),
			)
		} else {
			res.MessageID = msg.ID
			_ = r.store.TouchConversation(saveCtx, rc.Principal.ConversationID)
		}
	}

	_ = emit(sink, Event{Type: EventDone, Data: DoneData{
		MessageID: res.MessageID,
		Status:    res.Status,
		ElapsedMS: res.Elapsed.Milliseconds(),
		ToolCalls: res.ToolCalls,
	}})

	r.log.Info("对话轮次结束",
		zap.String("status", res.Status),
		zap.Uint64("message_id", res.MessageID),
		zap.Duration("elapsed", res.Elapsed),
		zap.Int("answer_chars", len([]rune(res.Answer))),
		zap.Strings("tool_calls", res.ToolCalls),
	)

	return res
}

// resolveStatus 根据回答与错误判定终态。
//
// 顺序关键：ctx 已取消必须优先于 runErr == nil 判断。
// 客户端断开时 Stream 本身可能正常返回 nil 错误，但 ctx 已被取消；
// 若先判 runErr == nil，这一轮会被误记为 completed，
// 用户看到的是「回答完整」，实际只收到半截。
func resolveStatus(answer string, runErr error, ctx context.Context) (status, content string) {
	cancelled := errors.Is(runErr, context.Canceled) ||
		errors.Is(runErr, context.DeadlineExceeded) ||
		ctx.Err() != nil

	if cancelled {
		// 保留已生成的半截文本；空时写占位说明，避免前端渲染空消息。
		if strings.TrimSpace(answer) == "" {
			answer = "[本轮生成已停止]"
		}
		return StatusCancelled, answer
	}

	if runErr == nil {
		// 工具轮次后模型可能不再输出文本：给明确占位。
		if strings.TrimSpace(answer) == "" {
			answer = "[已完成工具操作]"
		}
		return StatusCompleted, answer
	}

	return StatusFailed, answer
}

// userFacingError 把内部错误转成可展示信息。
//
// 原则：不泄露内部实现（SQL、文件路径、栈信息），
// 但要让用户知道「哪里出了问题、能不能重试」。
// 笼统的「生成失败」会让用户完全无法自助排查。
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
	// 工具参数不合法：模型生成的 JSON 有误，重试通常可以恢复
	case strings.Contains(msg, "failed to unmarshal arguments"):
		return "工具参数格式有误，请重试（通常是内容过长或含特殊字符）"
	// 模型未按预期调用工具
	case strings.Contains(msg, "failed to stream tool call"),
		strings.Contains(msg, "failed to invoke tool"):
		return "工具调用失败，请重试"
	case isTransient(err):
		return "上游服务暂时不可用，请重试"
	default:
		return "生成失败，请稍后重试"
	}
}

// withRunContext 把身份与运行状态注入 context。
//
// 这是工具获取用户身份的唯一来源：模型无法通过参数伪造用户 ID。
func withRunContext(ctx context.Context, rc *RunContext) context.Context {
	ctx = runtimeWithPrincipal(ctx, rc.Principal)
	return runtimeWithRunState(ctx, rc)
}
