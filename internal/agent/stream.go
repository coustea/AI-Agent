package agent

import (
	"context"
	"errors"
	"fmt"
	"io"
	"strings"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/schema"

	"mentorly/internal/dialogue"
)

// ErrEmptyAnswer 表示模型没有产出任何可用回答。
var ErrEmptyAnswer = errors.New("模型未返回有效回答")

// Chunk 是流式输出的一个片段。
// Text 非空表示增量文本；Reset 为 true 表示要求客户端清空已渲染内容
// （发生在模型调用工具前的过渡语之后——那段话不属于最终回答）。
type Chunk struct {
	Text  string
	Reset bool
}

// StreamResult 是一轮流式执行的最终结果。
type StreamResult struct {
	// Answer 最终回答（最后一次 reset 之后累积的全部文本）
	Answer string
	// Usage 模型返回的真实 token 用量，nil 表示供应商未返回
	Usage *schema.TokenUsage
	// ToolCalls 本轮调用过的工具名，便于观察与测试断言
	ToolCalls []string
	// Resets 触发 reset 的次数
	Resets int
	// HasToolOutput 本轮是否产生过工具结果消息（区别于「发起工具调用」）
	HasToolOutput bool
}

// accumulator 维护「当前回答缓冲区」。
//
// reset 语义：模型在调用工具前常先输出一句过渡语（如「让我看一下文件」），
// 然后发起工具调用，等工具返回后再输出真正的回答。过渡语不属于最终回答，
// 因此一旦检测到工具调用就要清空缓冲并通知客户端丢弃已渲染内容。
type accumulator struct {
	buf   strings.Builder
	sink  func(Chunk) error
	stats *StreamResult
}

// appendText 追加文本并推给客户端。
func (a *accumulator) appendText(text string) error {
	if text == "" {
		return nil
	}
	a.buf.WriteString(text)
	return emit(a.sink, Chunk{Text: text})
}

// reset 清空缓冲并通知客户端。
func (a *accumulator) reset() error {
	if a.buf.Len() == 0 {
		return nil
	}
	a.buf.Reset()
	a.stats.Resets++
	return emit(a.sink, Chunk{Reset: true})
}

// answer 返回当前累积的回答。
func (a *accumulator) answer() string {
	return strings.TrimSpace(a.buf.String())
}

// Stream 遍历 runner 的事件流，把增量文本推给 sink，并返回最终回答。
//
// 处理规则：
//   - 工具结果事件只记录工具名，内容不进回答；
//   - assistant 流式事件逐块读取、累积并推送；
//   - 一旦某个块携带 ToolCalls，立即 reset（丢弃此前的过渡语）；
//   - 捕获末包 ResponseMeta.Usage 作为真实用量；
//   - ctx 取消时立刻返回，由上层落库 cancelled。
func Stream(ctx context.Context, runner *adk.Runner, messages []*schema.Message, sink func(Chunk) error) (*StreamResult, error) {
	if runner == nil {
		return nil, fmt.Errorf("runner 为空")
	}

	iter := runner.Run(ctx, messages)

	res := &StreamResult{}
	acc := &accumulator{sink: sink, stats: res}

	for {
		// 先检查取消：客户端断开后不应继续消费事件。
		if err := ctx.Err(); err != nil {
			res.Answer = acc.answer()
			return res, err
		}

		event, ok := iter.Next()
		if !ok {
			break
		}
		if event.Err != nil {
			res.Answer = acc.answer()
			return res, event.Err
		}
		if event.Output == nil || event.Output.MessageOutput == nil {
			continue
		}

		mv := event.Output.MessageOutput

		// 工具结果事件：只记录名字。
		if mv.Role == schema.Tool {
			res.HasToolOutput = true
			if mv.ToolName != "" {
				res.ToolCalls = append(res.ToolCalls, mv.ToolName)
			}
			continue
		}

		// 只关心 assistant 输出。
		if mv.Role != "" && mv.Role != schema.Assistant {
			continue
		}

		if mv.IsStreaming && mv.MessageStream != nil {
			if err := consumeStream(ctx, mv.MessageStream, acc); err != nil {
				res.Answer = acc.answer()
				return res, err
			}
			continue
		}

		if mv.Message == nil {
			continue
		}

		msg := mv.Message

		// 非流式消息里携带工具调用：先 reset 掉过渡语。
		if len(msg.ToolCalls) > 0 {
			for _, tc := range msg.ToolCalls {
				if tc.Function.Name != "" {
					res.ToolCalls = append(res.ToolCalls, tc.Function.Name)
				}
			}
			if err := acc.reset(); err != nil {
				res.Answer = acc.answer()
				return res, err
			}
			continue
		}

		if msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil {
			res.Usage = msg.ResponseMeta.Usage
		}

		if err := acc.appendText(msg.Content); err != nil {
			res.Answer = acc.answer()
			return res, err
		}
	}

	res.Answer = acc.answer()
	if res.Answer == "" {
		// 调用了工具但最终没有文本输出：这不算「模型没回答」。
		// 典型场景是模型完成文件写入/读取后不再追加说明，
		// 或达到 MaxIterations 前最后一轮只有工具调用。
		// 这类情况应视为成功，只是回答为空，由上层决定如何呈现。
		if len(res.ToolCalls) > 0 || res.HasToolOutput {
			return res, nil
		}
		return res, ErrEmptyAnswer
	}

	return res, nil
}

// consumeStream 消费一个流式消息，逐块累积并推送。
func consumeStream(ctx context.Context, sr *schema.StreamReader[*schema.Message], acc *accumulator) error {
	// 必须关闭，否则底层 goroutine 泄漏。
	defer sr.Close()

	for {
		chunk, err := sr.Recv()
		if err != nil {
			if errors.Is(err, io.EOF) {
				return nil
			}
			// ctx 取消时 Recv 会返回错误，交给上层按取消处理。
			if ctxErr := ctx.Err(); ctxErr != nil {
				return ctxErr
			}
			return err
		}
		if chunk == nil {
			continue
		}

		// 末包带真实用量。
		if chunk.ResponseMeta != nil && chunk.ResponseMeta.Usage != nil {
			acc.stats.Usage = chunk.ResponseMeta.Usage
		}

		// 工具调用：记录名字并立即 reset（丢弃此前的过渡语）。
		if len(chunk.ToolCalls) > 0 {
			for _, tc := range chunk.ToolCalls {
				if tc.Function.Name != "" {
					acc.stats.ToolCalls = append(acc.stats.ToolCalls, tc.Function.Name)
				}
			}
			if err := acc.reset(); err != nil {
				return err
			}
			continue
		}

		if err := acc.appendText(chunk.Content); err != nil {
			return err
		}
	}
}

// emit 安全地调用 sink。
func emit(sink func(Chunk) error, c Chunk) error {
	if sink == nil {
		return nil
	}
	return sink(c)
}

// ToSchemaMessages 把领域消息转换成 eino schema 消息。
//
// 放在 agent 包是因为这是「喂给模型」的最后一步：
// dialogue 包不应依赖 eino，而 eino 的 schema 不该泄漏到其它层。
func ToSchemaMessages(msgs []dialogue.Message) []*schema.Message {
	out := make([]*schema.Message, 0, len(msgs)+1)
	for _, m := range msgs {
		if strings.TrimSpace(m.Content) == "" {
			continue
		}
		role := schema.User
		if m.Role == dialogue.RoleAssistant {
			role = schema.Assistant
		}
		out = append(out, &schema.Message{Role: role, Content: m.Content})
	}
	return out
}
