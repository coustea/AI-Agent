package llm

import (
	"encoding/json"
	"fmt"
	"strings"
)

// 本文件是 OpenAI 协议的纯函数编解码层：
// 输入输出只有 []byte 与结构体，不碰 http、不碰 channel、不碰 goroutine，
// 因此可以拿真实抓包报文做穷举式表驱动测试。

// sseDonePayload 是流结束标记。
const sseDonePayload = "[DONE]"

// ============================================================================
// 请求方向（领域模型 → OpenAI 报文）
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
	Role string `json:"role"`
	// Content 用指针表达三态：nil → null，指向空串 → ""。
	// assistant 携带 tool_calls 且无文本时必须发 null，发 "" 会被部分厂商判为非法。
	Content    *string       `json:"content"`
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

// encodeRequest 把领域请求编码为 OpenAI 协议报文。
// 优先使用 req.Model 动态覆盖；若为空则使用 Client 绑定的默认模型。
func encodeRequest(defaultModel string, req Request) ([]byte, error) {
	if len(req.Messages) == 0 {
		return nil, ErrEmptyMessages
	}

	model := strings.TrimSpace(req.Model)
	if model == "" {
		model = defaultModel
	}

	payload := reqPayload{
		Model:       model,
		Messages:    encodeMessages(req.Messages),
		Tools:       encodeTools(req.Tools),
		Temperature: req.Temperature,
		MaxTokens:   req.MaxTokens,
		Stream:      true,
		// 要求上游在最后一个 chunk 携带 usage；不声明则拿不到用量
		StreamOptions: &streamOptions{IncludeUsage: true},
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("llm: 编码请求失败: %w", err)
	}
	return data, nil
}

// encodeMessages 负责领域消息到协议消息的语义映射。
func encodeMessages(msgs []Message) []reqMessage {
	out := make([]reqMessage, 0, len(msgs))
	for _, m := range msgs {
		// 注意：ReasoningContent 只进不出，回传请求体中的 reasoning_content
		// 会被多数厂商判为非法字段，因此这里没有任何写入口。
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
// 响应方向（OpenAI 报文 → 语义化结果）
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

// wireToolCall 是流式分片：同一 index 的多次出现需要累积拼接。
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

// toolCallFragment 是一次分片到达的工具调用片段。
type toolCallFragment struct {
	index int
	id    string
	name  string
	args  string
}

// decoded 是一条 SSE data 的语义化结果，不含任何生命周期判断。
type decoded struct {
	delta     string
	reasoning string
	fragments []toolCallFragment
	usage     *Usage
	finish    StopReason
	hasFinish bool
	apiErr    string
}

// decodeData 解析一条 SSE data 载荷。
func decodeData(data []byte) (decoded, error) {
	var w wireChunk
	if err := json.Unmarshal(data, &w); err != nil {
		return decoded{}, fmt.Errorf("%w: %s", ErrProtocolViolation, clip(string(data), 200))
	}

	var d decoded

	// 厂商错误信封：{"error":{"message":...}}，必须显式识别，不能当作"空 chunk"跳过
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

	// choices 可能为空数组：纯 usage chunk 就长这样
	if len(w.Choices) == 0 {
		return d, nil
	}

	choice := w.Choices[0]
	d.delta = choice.Delta.Content
	d.reasoning = choice.Delta.ReasoningContent
	if d.reasoning == "" {
		d.reasoning = choice.Delta.Reasoning
	}

	for _, tc := range choice.Delta.ToolCalls {
		frag := toolCallFragment{index: tc.Index, id: tc.ID}
		if tc.Function != nil {
			frag.name = tc.Function.Name
			frag.args = tc.Function.Arguments
		}
		d.fragments = append(d.fragments, frag)
	}

	if choice.FinishReason != nil {
		d.finish = stopReason(*choice.FinishReason)
		d.hasFinish = true
	}

	return d, nil
}

// stopReason 把厂商的 finish_reason 映射为领域终止原因。
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

// errorMessage 从响应体中提取上游错误描述。
func errorMessage(body string) string {
	if strings.TrimSpace(body) == "" {
		return ""
	}
	var envelope struct {
		Error *wireError `json:"error"`
	}
	if err := json.Unmarshal([]byte(body), &envelope); err == nil && envelope.Error != nil && envelope.Error.Message != "" {
		return envelope.Error.Message
	}
	var alt struct {
		Message string `json:"message"`
	}
	if err := json.Unmarshal([]byte(body), &alt); err == nil && alt.Message != "" {
		return alt.Message
	}
	return ""
}

// clip 按字符（而非字节）截断，避免切碎多字节字符。
func clip(s string, limit int) string {
	s = strings.TrimSpace(s)
	runes := []rune(s)
	if len(runes) <= limit {
		return s
	}
	return string(runes[:limit]) + "…"
}
