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

var (
	ErrEmptyAPIKey   = errors.New("llm: api key cannot be empty")
	ErrEmptyMessages = errors.New("llm: messages cannot be empty")
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
	Role       string         `json:"role"`
	Content    *string        `json:"content"`
	Name       string         `json:"name,omitempty"`
	ToolCallID string         `json:"tool_call_id,omitempty"`
	ToolCalls  []wireToolCall `json:"tool_calls,omitempty"`
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

// toWireMessages 将统一 Message 转为 OpenAI 协议规范格式
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

		// reasoning_content 只进不出：入站提取供上层展示与存储，
		// 但回传请求体中严禁包含该字段（多数厂商 API 会直接返回 400）。

		if m.Role == RoleTool && m.ToolResult != nil {
			msg.ToolCallID = m.ToolResult.ToolCallID
			msg.Name = m.ToolResult.Name
			s := m.ToolResult.Content
			msg.Content = &s
		}

		if m.Role == RoleAssistant && len(m.ToolCalls) > 0 {
			tcs := make([]wireToolCall, 0, len(m.ToolCalls))
			for _, tc := range m.ToolCalls {
				tcs = append(tcs, wireToolCall{
					ID:   tc.ID,
					Type: "function",
					Function: wireFunc{
						Name:      tc.Name,
						Arguments: tc.Arguments,
					},
				})
			}
			msg.ToolCalls = tcs
		}

		out = append(out, msg)
	}
	return out
}

// toWireTools 将统一工具定义转为 OpenAI 协议规范格式
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

// ResolveChatURL 根据 baseURL 智能拼接 chat completions 端点路径
func ResolveChatURL(base string) string {
	base = strings.TrimRight(strings.TrimSpace(base), "/")
	if strings.HasSuffix(base, "/chat/completions") {
		return base
	}
	if strings.HasSuffix(base, "/openai") || strings.HasSuffix(base, "/v1") || strings.HasSuffix(base, "/v2") {
		return base + "/chat/completions"
	}
	return base + "/v1/chat/completions"
}

// BuildRequestPayload 序列化 OpenAI 协议请求体
func BuildRequestPayload(model string, req *ChatRequest, stream bool) ([]byte, error) {
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
		return nil, fmt.Errorf("llm: marshal request: %w", err)
	}
	return payload, nil
}

// buildHTTPRequest 从 payload 构建 HTTP 请求对象
func buildHTTPRequest(ctx context.Context, url string, payload []byte, stream bool) (*http.Request, error) {
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("llm: create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	if stream {
		httpReq.Header.Set("Accept", "text/event-stream")
	}

	return httpReq, nil
}

type tcBuilder struct {
	id   string
	name strings.Builder
	args strings.Builder
}

// readSSE 读取 SSE 数据流并向 channel 逐块发送增量，返回整轮累计 Usage
func readSSE(ctx context.Context, reader io.Reader, out chan<- ChatResponse) Usage {
	scanner := bufio.NewReader(reader)
	var turnUsage Usage
	tcMap := make(map[int]*tcBuilder)

	for {
		line, err := scanner.ReadString('\n')
		if err != nil {
			if err == io.EOF {
				break
			}
			sendChunk(ctx, out, ChatResponse{Err: fmt.Errorf("llm: stream read: %w", err)})
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
			if !sendChunk(ctx, out, ChatResponse{ReasoningContent: choice.Delta.ReasoningContent}) {
				return turnUsage
			}
		}
		if choice.Delta.Content != "" {
			if !sendChunk(ctx, out, ChatResponse{Delta: choice.Delta.Content}) {
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
				Arguments: b.args.String(),
			})
		}
	}

	sendChunk(ctx, out, ChatResponse{
		Done:      true,
		ToolCalls: finalTCs,
		Usage:     &turnUsage,
	})

	return turnUsage
}

// sendChunk 安全向 channel 发送 ChatResponse，感知 context 取消
func sendChunk(ctx context.Context, ch chan<- ChatResponse, chunk ChatResponse) bool {
	select {
	case ch <- chunk:
		return true
	case <-ctx.Done():
		return false
	}
}

func isRetryableNetworkError(err error) bool {
	if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
		return false
	}
	return true
}

func sleepBackoff(ctx context.Context, attempt int) error {
	baseDelay := 150 * time.Millisecond
	delay := time.Duration(1<<(attempt-1)) * baseDelay
	timer := time.NewTimer(delay)
	defer timer.Stop()

	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}
