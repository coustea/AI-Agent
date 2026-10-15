package gateway

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strings"
)

// --- OpenAI 协议内部 wire 结构体 ---

type wireFunc struct {
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
}

type wireToolCall struct {
	Index    *int     `json:"index,omitempty"`
	ID       string   `json:"id,omitempty"`
	Type     string   `json:"type"`
	Function wireFunc `json:"function"`
}

type wireTool struct {
	Type     string         `json:"type"`
	Function ToolDefinition `json:"function"`
}

type wireMsg struct {
	Role             string         `json:"role"`
	Content          *string        `json:"content"`
	ReasoningContent *string        `json:"reasoning_content,omitempty"`
	Name             string         `json:"name,omitempty"`
	ToolCallID       string         `json:"tool_call_id,omitempty"`
	ToolCalls        []wireToolCall `json:"tool_calls,omitempty"`
}

type wireReq struct {
	Model         string     `json:"model"`
	Messages      []wireMsg  `json:"messages"`
	Tools         []wireTool `json:"tools,omitempty"`
	Temperature   *float32   `json:"temperature,omitempty"`
	MaxTokens     *int       `json:"max_tokens,omitempty"`
	Stream        bool       `json:"stream,omitempty"`
	StreamOptions any        `json:"stream_options,omitempty"`
}

type wireUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

type wireResp struct {
	Choices []struct {
		Message struct {
			Role             string         `json:"role"`
			Content          string         `json:"content"`
			ReasoningContent string         `json:"reasoning_content,omitempty"`
			ToolCalls        []wireToolCall `json:"tool_calls"`
		} `json:"message"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
	Usage *wireUsage `json:"usage"`
}

type wireChunk struct {
	Choices []struct {
		Delta struct {
			Role             string         `json:"role"`
			Content          string         `json:"content"`
			ReasoningContent string         `json:"reasoning_content,omitempty"`
			ToolCalls        []wireToolCall `json:"tool_calls"`
		} `json:"delta"`
		FinishReason *string `json:"finish_reason"`
	} `json:"choices"`
	Usage *wireUsage `json:"usage"`
}

// --- 共享转换与协议处理函数 ---

// toWireMessages 将统一 Message 转为 OpenAI wire 格式
func toWireMessages(messages []Message) []wireMsg {
	out := make([]wireMsg, 0, len(messages))
	for _, m := range messages {
		msg := wireMsg{
			Role: string(m.Role),
		}

		if m.Content != "" || (m.Role != RoleAssistant && m.Role != RoleTool) {
			s := m.Content
			msg.Content = &s
		}

		if m.ReasoningContent != "" {
			s := m.ReasoningContent
			msg.ReasoningContent = &s
		}

		if m.Role == RoleTool && m.ToolResult != nil {
			msg.ToolCallID = m.ToolResult.ToolCallID
			msg.Name = m.ToolResult.Name
			s := m.ToolResult.Content
			msg.Content = &s
		}

		if m.Role == RoleAssistant && len(m.ToolCalls) > 0 {
			if msg.ReasoningContent == nil {
				empty := ""
				msg.ReasoningContent = &empty
			}
			tcs := make([]wireToolCall, 0, len(m.ToolCalls))
			for _, tc := range m.ToolCalls {
				tcs = append(tcs, wireToolCall{
					ID:   tc.ID,
					Type: "function",
					Function: wireFunc{
						Name:      tc.Name,
						Arguments: string(tc.Arguments),
					},
				})
			}
			msg.ToolCalls = tcs
		}

		out = append(out, msg)
	}
	return out
}

// toWireTools 将统一工具定义转为 OpenAI wire 格式
func toWireTools(tools []ToolDefinition) []wireTool {
	if len(tools) == 0 {
		return nil
	}
	out := make([]wireTool, 0, len(tools))
	for _, t := range tools {
		out = append(out, wireTool{Type: "function", Function: t})
	}
	return out
}

// chatURL 根据 baseURL 智能拼接 chat completions 端点路径
func chatURL(base string) string {
	base = strings.TrimRight(strings.TrimSpace(base), "/")
	if strings.HasSuffix(base, "/chat/completions") {
		return base
	}
	if strings.HasSuffix(base, "/openai") || strings.HasSuffix(base, "/v1") {
		return base + "/chat/completions"
	}
	return base + "/v1/chat/completions"
}

// buildHTTPRequest 构建 OpenAI 协议的 HTTP 请求体
func buildHTTPRequest(ctx context.Context, url string, model string, req *ChatRequest, stream bool) (*http.Request, error) {
	if req == nil || len(req.Messages) == 0 {
		return nil, ErrEmptyMessages
	}

	if strings.TrimSpace(req.Model) != "" {
		model = strings.TrimSpace(req.Model)
	}

	body := wireReq{
		Model:       model,
		Messages:    toWireMessages(req.Messages),
		Tools:       toWireTools(req.Tools),
		Temperature: req.Temperature,
		MaxTokens:   req.MaxTokens,
		Stream:      stream,
	}
	if stream {
		body.StreamOptions = map[string]any{"include_usage": true}
	}

	payload, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("gateway: marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("gateway: create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	if stream {
		httpReq.Header.Set("Accept", "text/event-stream")
	}

	return httpReq, nil
}

// parseResponse 解析同步响应 body
func parseResponse(bodyBytes []byte) (string, []ToolCall, Usage, error) {
	var res wireResp
	if err := json.Unmarshal(bodyBytes, &res); err != nil {
		return "", nil, Usage{}, fmt.Errorf("gateway: json decode: %w", err)
	}
	if len(res.Choices) == 0 {
		return "", nil, Usage{}, fmt.Errorf("gateway: no choices in response")
	}

	choice := res.Choices[0]
	toolCalls := make([]ToolCall, 0, len(choice.Message.ToolCalls))
	for _, tc := range choice.Message.ToolCalls {
		toolCalls = append(toolCalls, ToolCall{
			ID:        tc.ID,
			Name:      tc.Function.Name,
			Arguments: json.RawMessage(tc.Function.Arguments),
		})
	}

	var usage Usage
	if res.Usage != nil {
		usage = Usage{
			PromptTokens:     res.Usage.PromptTokens,
			CompletionTokens: res.Usage.CompletionTokens,
			TotalTokens:      res.Usage.TotalTokens,
		}
	}

	return choice.Message.Content, toolCalls, usage, nil
}

type tcBuilder struct {
	id   string
	name strings.Builder
	args strings.Builder
}

// readSSE 读取 SSE 流并向 channel 逐块发送，返回累计 Usage
func readSSE(ctx context.Context, reader io.Reader, out chan<- StreamChunk) Usage {
	scanner := bufio.NewReader(reader)
	var turnUsage Usage
	tcMap := make(map[int]*tcBuilder)

	for {
		line, err := scanner.ReadString('\n')
		if err != nil {
			if err == io.EOF {
				break
			}
			sendChunk(ctx, out, StreamChunk{Err: fmt.Errorf("gateway: stream read: %w", err)})
			return turnUsage
		}

		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, ":") {
			continue
		}
		if !strings.HasPrefix(line, "data:") {
			continue
		}

		data := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
		if data == "[DONE]" {
			break
		}

		var chunk wireChunk
		if err := json.Unmarshal([]byte(data), &chunk); err != nil {
			continue
		}

		if chunk.Usage != nil {
			turnUsage = Usage{
				PromptTokens:     chunk.Usage.PromptTokens,
				CompletionTokens: chunk.Usage.CompletionTokens,
				TotalTokens:      chunk.Usage.TotalTokens,
			}
		}

		if len(chunk.Choices) == 0 {
			continue
		}

		choice := chunk.Choices[0]
		if choice.Delta.ReasoningContent != "" {
			sendChunk(ctx, out, StreamChunk{ReasoningContent: choice.Delta.ReasoningContent})
		}
		if choice.Delta.Content != "" {
			if !sendChunk(ctx, out, StreamChunk{Delta: choice.Delta.Content}) {
				return turnUsage
			}
		}

		for _, tc := range choice.Delta.ToolCalls {
			idx := 0
			if tc.Index != nil {
				idx = *tc.Index
			}
			b, exists := tcMap[idx]
			if !exists {
				b = &tcBuilder{}
				tcMap[idx] = b
			}
			if tc.ID != "" {
				b.id = tc.ID
			}
			if tc.Function.Name != "" {
				b.name.WriteString(tc.Function.Name)
			}
			if tc.Function.Arguments != "" {
				b.args.WriteString(tc.Function.Arguments)
			}
		}
	}

	var finalTCs []ToolCall
	if len(tcMap) > 0 {
		indices := make([]int, 0, len(tcMap))
		for idx := range tcMap {
			indices = append(indices, idx)
		}
		sort.Ints(indices)
		for _, idx := range indices {
			b := tcMap[idx]
			finalTCs = append(finalTCs, ToolCall{
				ID:        b.id,
				Name:      b.name.String(),
				Arguments: json.RawMessage(b.args.String()),
			})
		}
	}

	sendChunk(ctx, out, StreamChunk{
		Done:      true,
		ToolCalls: finalTCs,
		Usage:     &turnUsage,
	})

	return turnUsage
}

// sendChunk 安全地向 channel 发送一个 StreamChunk
func sendChunk(ctx context.Context, ch chan<- StreamChunk, chunk StreamChunk) bool {
	select {
	case ch <- chunk:
		return true
	case <-ctx.Done():
		return false
	}
}
