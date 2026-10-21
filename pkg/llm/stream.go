package llm

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strings"
	"time"
)

const (
	sseDonePayload = "[DONE]"
	streamBufSize  = 64 << 10
	terminalGrace  = 200 * time.Millisecond
)

// ============================================================================
// 请求编码（领域模型 → OpenAI 兼容 Wire 协议）
// ============================================================================

type reqPayload struct {
	Model         string         `json:"model"`
	Messages      []reqMessage   `json:"messages"`
	Tools         []reqTool      `json:"tools,omitempty"`
	Temperature   *float32       `json:"temperature,omitempty"`
	MaxTokens     *int           `json:"max_tokens,omitempty"`
	Stream        bool           `json:"stream"`
	StreamOptions *streamOptions `json:"stream_options,omitempty"`
}

type streamOptions struct {
	IncludeUsage bool `json:"include_usage"`
}

type reqMessage struct {
	Role       string        `json:"role"`
	Content    *string       `json:"content"` // nil → null; 部分厂商在 tool_calls 下要求 content 为 null
	ToolCalls  []reqToolCall `json:"tool_calls,omitempty"`
	ToolCallID string        `json:"tool_call_id,omitempty"`
	Name       string        `json:"name,omitempty"`
}

type reqToolCall struct {
	ID       string      `json:"id"`
	Type     string      `json:"type"`
	Function reqFunction `json:"function"`
}

type reqFunction struct {
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
}

type reqTool struct {
	Type     string         `json:"type"`
	Function ToolDefinition `json:"function"`
}

func encodeRequest(defaultModel string, req Request) ([]byte, error) {
	if len(req.Messages) == 0 {
		return nil, ErrEmptyMessages
	}

	model := strings.TrimSpace(req.Model)
	if model == "" {
		model = defaultModel
	}
	if model == "" {
		return nil, ErrEmptyModel
	}

	payload := reqPayload{
		Model:         model,
		Messages:      encodeMessages(req.Messages),
		Tools:         encodeTools(req.Tools),
		Temperature:   req.Temperature,
		MaxTokens:     req.MaxTokens,
		Stream:        true,
		StreamOptions: &streamOptions{IncludeUsage: true},
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("llm: 编码请求失败: %w", err)
	}
	return data, nil
}

func encodeMessages(msgs []Message) []reqMessage {
	out := make([]reqMessage, 0, len(msgs))
	for _, m := range msgs {
		rm := reqMessage{Role: string(m.Role)}
		switch m.Role {
		case RoleTool:
			if m.ToolResult != nil {
				rm.ToolCallID = m.ToolResult.ToolCallID
				rm.Name = m.ToolResult.Name
				content := m.ToolResult.Content
				rm.Content = &content
			}
		case RoleAssistant:
			// assistant 携带 tool_calls 且无文本时发 null，发 "" 会被部分厂商判为非法
			if m.Content != "" {
				content := m.Content
				rm.Content = &content
			}
			if len(m.ToolCalls) > 0 {
				rm.ToolCalls = encodeToolCalls(m.ToolCalls)
			}
		default:
			content := m.Content
			rm.Content = &content
		}
		out = append(out, rm)
	}
	return out
}

func encodeToolCalls(calls []ToolCall) []reqToolCall {
	out := make([]reqToolCall, 0, len(calls))
	for _, c := range calls {
		out = append(out, reqToolCall{
			ID:       c.ID,
			Type:     "function",
			Function: reqFunction{Name: c.Name, Arguments: c.Arguments},
		})
	}
	return out
}

func encodeTools(tools []ToolDefinition) []reqTool {
	if len(tools) == 0 {
		return nil
	}
	out := make([]reqTool, 0, len(tools))
	for _, t := range tools {
		out = append(out, reqTool{Type: "function", Function: t})
	}
	return out
}

// ============================================================================
// 响应解码（Wire 协议 → 语义化结果）
// ============================================================================

type wireChunk struct {
	Choices []wireChoice `json:"choices"`
	Usage   *wireUsage   `json:"usage"`
	Error   *wireError   `json:"error"`
}

type wireChoice struct {
	Delta        wireDelta `json:"delta"`
	FinishReason *string   `json:"finish_reason"`
}

type wireDelta struct {
	Content          string         `json:"content"`
	ReasoningContent string         `json:"reasoning_content"`
	Reasoning        string         `json:"reasoning"`
	ToolCalls        []wireToolCall `json:"tool_calls"`
}

type wireToolCall struct {
	Index    int           `json:"index"`
	ID       string        `json:"id"`
	Function *wireFunction `json:"function"`
}

type wireFunction struct {
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
}

type wireUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

type wireError struct {
	Message string `json:"message"`
	Type    string `json:"type"`
	Code    any    `json:"code"`
}

type decoded struct {
	delta     string
	reasoning string
	toolCalls []wireToolCall
	usage     *Usage
	finish    StopReason
	hasFinish bool
	apiErr    string
}

func decodeData(data []byte) (decoded, error) {
	var w wireChunk
	if err := json.Unmarshal(data, &w); err != nil {
		return decoded{}, fmt.Errorf("%w: %s", ErrProtocolViolation, clip(string(data), 200))
	}

	var d decoded
	if w.Error != nil {
		d.apiErr = w.Error.Message
		if d.apiErr == "" {
			d.apiErr = clip(string(data), 200)
		}
		return d, nil
	}

	if w.Usage != nil {
		d.usage = &Usage{
			PromptTokens:     w.Usage.PromptTokens,
			CompletionTokens: w.Usage.CompletionTokens,
			TotalTokens:      w.Usage.TotalTokens,
		}
	}

	if len(w.Choices) == 0 {
		return d, nil
	}

	choice := w.Choices[0]
	d.delta = choice.Delta.Content
	d.reasoning = choice.Delta.ReasoningContent
	if d.reasoning == "" {
		d.reasoning = choice.Delta.Reasoning
	}
	d.toolCalls = choice.Delta.ToolCalls

	if choice.FinishReason != nil {
		d.finish = stopReason(*choice.FinishReason)
		d.hasFinish = true
	}

	return d, nil
}

func stopReason(raw string) StopReason {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "tool_calls", "function_call":
		return StopToolCalls
	case "length", "max_tokens":
		return StopLength
	case "content_filter":
		return StopContentFilter
	default:
		return StopEnd
	}
}

// extractErrorMessage 单次 Unmarshal 提取错误描述。
func extractErrorMessage(body string) string {
	body = strings.TrimSpace(body)
	if body == "" {
		return ""
	}
	var env struct {
		Error   *wireError `json:"error"`
		Message string     `json:"message"`
	}
	if err := json.Unmarshal([]byte(body), &env); err == nil {
		if env.Error != nil && env.Error.Message != "" {
			return env.Error.Message
		}
		return env.Message
	}
	return ""
}

func clip(s string, limit int) string {
	s = strings.TrimSpace(s)
	runes := []rune(s)
	if len(runes) <= limit {
		return s
	}
	return string(runes[:limit]) + "…"
}

// ============================================================================
// 流式泵与事件还原
// ============================================================================

type outcome struct {
	usage     Usage
	toolCalls []ToolCall
	finish    StopReason
	err       error
}

func pump(ctx context.Context, cancel context.CancelFunc, resp *http.Response) <-chan Chunk {
	out := make(chan Chunk, 32)

	go func() {
		defer close(out)
		defer cancel()
		defer func() { _ = resp.Body.Close() }()

		res := readSSE(ctx, resp.Body, out)
		deliverTerminal(out, Chunk{
			ToolCalls: res.toolCalls,
			Usage:     res.usage,
			Finish:    res.finish,
			Err:       res.err,
		})
	}()

	return out
}

func readSSE(ctx context.Context, body io.Reader, out chan<- Chunk) outcome {
	reader := bufio.NewReaderSize(body, streamBufSize)
	acc := newToolCallAccumulator()
	res := outcome{}

	for {
		line, readErr := reader.ReadBytes('\n')

		// 零拷贝直接处理字节切片
		if payload, ok := ssePayloadBytes(line); ok {
			if bytes.Equal(payload, []byte(sseDonePayload)) {
				if res.finish == "" {
					res.finish = StopEnd
				}
				return finishWith(res, acc, res.finish, nil)
			}

			d, err := decodeData(payload)
			switch {
			case err != nil:
				return finishWith(res, acc, StopFailed, err)
			case d.apiErr != "":
				return finishWith(res, acc, StopFailed, fmt.Errorf("llm: 上游在流中返回错误: %s", d.apiErr))
			}

			if d.usage != nil {
				res.usage = *d.usage
			}
			acc.add(d.toolCalls)

			if d.reasoning != "" && !sendChunk(ctx, out, Chunk{ReasoningContent: d.reasoning}) {
				return finishWith(res, acc, StopCanceled, ctx.Err())
			}
			if d.delta != "" && !sendChunk(ctx, out, Chunk{Delta: d.delta}) {
				return finishWith(res, acc, StopCanceled, ctx.Err())
			}
			if d.hasFinish {
				res.finish = d.finish
			}
		}

		if readErr == nil {
			continue
		}

		switch {
		case errors.Is(readErr, io.EOF):
			if res.finish != "" {
				return finishWith(res, acc, res.finish, nil)
			}
			return finishWith(res, acc, StopTruncated, ErrStreamTruncated)
		case ctx.Err() != nil:
			return finishWith(res, acc, StopCanceled, ctx.Err())
		default:
			return finishWith(res, acc, StopFailed, fmt.Errorf("llm: 读取流失败: %w", readErr))
		}
	}
}

func finishWith(res outcome, acc *toolCallAccumulator, finish StopReason, err error) outcome {
	res.finish = finish
	res.err = err
	res.toolCalls = acc.result()
	return res
}

func ssePayloadBytes(line []byte) ([]byte, bool) {
	line = bytes.TrimRight(line, "\r\n")
	if len(line) == 0 || line[0] == ':' {
		return nil, false
	}
	if !bytes.HasPrefix(line, []byte("data:")) {
		return nil, false
	}
	payload := bytes.TrimSpace(bytes.TrimPrefix(line, []byte("data:")))
	if len(payload) == 0 {
		return nil, false
	}
	return payload, true
}

func sendChunk(ctx context.Context, out chan<- Chunk, chunk Chunk) bool {
	select {
	case out <- chunk:
		return true
	case <-ctx.Done():
		return false
	}
}

func deliverTerminal(out chan<- Chunk, terminal Chunk) {
	timer := time.NewTimer(terminalGrace)
	defer timer.Stop()

	select {
	case out <- terminal:
	case <-timer.C:
	}
}

// ============================================================================
// 流式工具调用还原器
// ============================================================================

type toolCallAccumulator struct {
	order []int
	byIdx map[int]*toolCallBuilder
}

type toolCallBuilder struct {
	id   string
	name strings.Builder
	args strings.Builder
}

func newToolCallAccumulator() *toolCallAccumulator {
	return &toolCallAccumulator{byIdx: make(map[int]*toolCallBuilder)}
}

func (a *toolCallAccumulator) add(calls []wireToolCall) {
	for _, tc := range calls {
		builder, ok := a.byIdx[tc.Index]
		if !ok {
			builder = &toolCallBuilder{}
			a.byIdx[tc.Index] = builder
			a.order = append(a.order, tc.Index)
		}
		if tc.ID != "" {
			builder.id = tc.ID
		}
		if tc.Function != nil {
			builder.name.WriteString(tc.Function.Name)
			builder.args.WriteString(tc.Function.Arguments)
		}
	}
}

func (a *toolCallAccumulator) result() []ToolCall {
	if len(a.order) == 0 {
		return nil
	}
	sort.Ints(a.order)

	out := make([]ToolCall, 0, len(a.order))
	for _, idx := range a.order {
		builder := a.byIdx[idx]
		out = append(out, ToolCall{
			ID:        builder.id,
			Name:      builder.name.String(),
			Arguments: builder.args.String(),
		})
	}
	return out
}
