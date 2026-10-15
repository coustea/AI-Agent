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
	"sync"

	"my-agent/internal/config"
)

// LlamaCppGateway 通过 llama.cpp 的 HTTP 服务模式 (llama-server) 进行同步与流式模型调用。
// 纯 Go 标准库实现，无需 Cgo，默认请求 http://127.0.0.1:8080/v1/chat/completions。
type LlamaCppGateway struct {
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client

	mu         sync.RWMutex
	totalUsage Usage
}

// NewLlamaCppGateway 创建 llama.cpp 网关适配器实例。
func NewLlamaCppGateway(baseURL, apiKey, defaultModel string, client *http.Client) (*LlamaCppGateway, error) {
	baseURL = strings.TrimSpace(baseURL)
	if baseURL == "" {
		baseURL = config.DefaultLlamaCppBaseURL
	}
	baseURL = strings.TrimRight(baseURL, "/")

	if strings.TrimSpace(defaultModel) == "" {
		defaultModel = config.DefaultLlamaCppModel
	}

	if client == nil {
		client = http.DefaultClient
	}

	return &LlamaCppGateway{
		baseURL:    baseURL,
		apiKey:     strings.TrimSpace(apiKey),
		model:      strings.TrimSpace(defaultModel),
		httpClient: client,
	}, nil
}

// CheckHealth 检查本地 llama-server 服务健康与模型加载状态。
func (g *LlamaCppGateway) CheckHealth(ctx context.Context) error {
	url := g.baseURL + "/health"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return fmt.Errorf("llamacpp: failed to create health request: %w", err)
	}

	resp, err := g.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("llamacpp: server unreachable at %s: %w", g.baseURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		return nil
	}

	if resp.StatusCode == http.StatusServiceUnavailable {
		return fmt.Errorf("llamacpp: server is still loading model (503 Service Unavailable)")
	}

	body, _ := io.ReadAll(resp.Body)
	return fmt.Errorf("llamacpp: health check returned status %d: %s", resp.StatusCode, string(body))
}

// --- Wire 协议请求与响应 DTO ---

type llamaCppFunctionCallDTO struct {
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
}

type llamaCppToolCallDTO struct {
	Index    *int                    `json:"index,omitempty"`
	ID       string                  `json:"id,omitempty"`
	Type     string                  `json:"type"`
	Function llamaCppFunctionCallDTO `json:"function"`
}

type llamaCppToolDTO struct {
	Type     string         `json:"type"`
	Function ToolDefinition `json:"function"`
}

type llamaCppMessageDTO struct {
	Role             string                `json:"role"`
	Content          *string               `json:"content"`
	ReasoningContent *string               `json:"reasoning_content,omitempty"`
	Name             string                `json:"name,omitempty"`
	ToolCallID       string                `json:"tool_call_id,omitempty"`
	ToolCalls        []llamaCppToolCallDTO `json:"tool_calls,omitempty"`
}

type llamaCppChatRequestDTO struct {
	Model         string               `json:"model"`
	Messages      []llamaCppMessageDTO `json:"messages"`
	Tools         []llamaCppToolDTO    `json:"tools,omitempty"`
	Temperature   *float32             `json:"temperature,omitempty"`
	MaxTokens     *int                 `json:"max_tokens,omitempty"`
	Stream        bool                 `json:"stream,omitempty"`
	StreamOptions any                  `json:"stream_options,omitempty"`
}

type llamaCppUsageDTO struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

type llamaCppChatResponseDTO struct {
	Choices []struct {
		Message struct {
			Role             string                `json:"role"`
			Content          string                `json:"content"`
			ReasoningContent string                `json:"reasoning_content,omitempty"`
			ToolCalls        []llamaCppToolCallDTO `json:"tool_calls"`
		} `json:"message"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
	Usage *llamaCppUsageDTO `json:"usage"`
}

type llamaCppStreamChunkDTO struct {
	Choices []struct {
		Delta struct {
			Role             string                `json:"role"`
			Content          string                `json:"content"`
			ReasoningContent string                `json:"reasoning_content,omitempty"`
			ToolCalls        []llamaCppToolCallDTO `json:"tool_calls"`
		} `json:"delta"`
		FinishReason *string `json:"finish_reason"`
	} `json:"choices"`
	Usage *llamaCppUsageDTO `json:"usage"`
}

func (g *LlamaCppGateway) convertMessages(messages []Message) []llamaCppMessageDTO {
	out := make([]llamaCppMessageDTO, 0, len(messages))
	for _, m := range messages {
		dto := llamaCppMessageDTO{
			Role: string(m.Role),
		}

		if m.Content != "" || (m.Role != RoleAssistant && m.Role != RoleTool) {
			contentStr := m.Content
			dto.Content = &contentStr
		}

		if m.ReasoningContent != "" {
			reasoningStr := m.ReasoningContent
			dto.ReasoningContent = &reasoningStr
		}

		if m.Role == RoleTool && m.ToolResult != nil {
			dto.ToolCallID = m.ToolResult.ToolCallID
			dto.Name = m.ToolResult.Name
			contentStr := m.ToolResult.Content
			dto.Content = &contentStr
		}

		if m.Role == RoleAssistant && len(m.ToolCalls) > 0 {
			// DeepSeek V4+ 要求如果携带 ToolCalls 且在思考模式下必须传递 reasoning_content (可为空字符串)
			if dto.ReasoningContent == nil {
				emptyReasoning := ""
				dto.ReasoningContent = &emptyReasoning
			}
			toolCallsDTO := make([]llamaCppToolCallDTO, 0, len(m.ToolCalls))
			for _, tc := range m.ToolCalls {
				toolCallsDTO = append(toolCallsDTO, llamaCppToolCallDTO{
					ID:   tc.ID,
					Type: "function",
					Function: llamaCppFunctionCallDTO{
						Name:      tc.Name,
						Arguments: string(tc.Arguments),
					},
				})
			}
			dto.ToolCalls = toolCallsDTO
		}

		out = append(out, dto)
	}
	return out
}

func (g *LlamaCppGateway) buildRequest(ctx context.Context, req *ChatRequest, stream bool) (*http.Request, error) {
	if req == nil || len(req.Messages) == 0 {
		return nil, ErrEmptyMessages
	}

	model := strings.TrimSpace(req.Model)
	if model == "" {
		model = g.model
	}

	bodyDTO := llamaCppChatRequestDTO{
		Model:       model,
		Messages:    g.convertMessages(req.Messages),
		Temperature: req.Temperature,
		MaxTokens:   req.MaxTokens,
		Stream:      stream,
	}

	if len(req.Tools) > 0 {
		toolsDTO := make([]llamaCppToolDTO, 0, len(req.Tools))
		for _, t := range req.Tools {
			toolsDTO = append(toolsDTO, llamaCppToolDTO{
				Type:     "function",
				Function: t,
			})
		}
		bodyDTO.Tools = toolsDTO
	}

	if stream {
		bodyDTO.StreamOptions = map[string]any{"include_usage": true}
	}

	payload, err := json.Marshal(bodyDTO)
	if err != nil {
		return nil, fmt.Errorf("llamacpp: failed to marshal request: %w", err)
	}

	url := g.baseURL + "/v1/chat/completions"
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("llamacpp: failed to create http request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	if g.apiKey != "" {
		httpReq.Header.Set("Authorization", "Bearer "+g.apiKey)
	}
	if stream {
		httpReq.Header.Set("Accept", "text/event-stream")
	}

	return httpReq, nil
}

// Chat 执行同步对话调用
func (g *LlamaCppGateway) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	httpReq, err := g.buildRequest(ctx, req, false)
	if err != nil {
		return nil, err
	}

	resp, err := g.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("llamacpp: http post error: %w", err)
	}
	defer resp.Body.Close()

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("llamacpp: read response body error: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("llamacpp: server returned error status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	var resDTO llamaCppChatResponseDTO
	if err := json.Unmarshal(bodyBytes, &resDTO); err != nil {
		return nil, fmt.Errorf("llamacpp: json decode error: %w", err)
	}

	if len(resDTO.Choices) == 0 {
		return nil, fmt.Errorf("llamacpp: no choices in response")
	}

	choice := resDTO.Choices[0]
	toolCalls := make([]ToolCall, 0, len(choice.Message.ToolCalls))
	for _, tc := range choice.Message.ToolCalls {
		toolCalls = append(toolCalls, ToolCall{
			ID:        tc.ID,
			Name:      tc.Function.Name,
			Arguments: json.RawMessage(tc.Function.Arguments),
		})
	}

	var usage Usage
	if resDTO.Usage != nil {
		usage = Usage{
			PromptTokens:     resDTO.Usage.PromptTokens,
			CompletionTokens: resDTO.Usage.CompletionTokens,
			TotalTokens:      resDTO.Usage.TotalTokens,
		}
		g.mu.Lock()
		g.totalUsage.Add(usage)
		g.mu.Unlock()
	}

	return &ChatResponse{
		Content:   choice.Message.Content,
		ToolCalls: toolCalls,
		Usage:     usage,
	}, nil
}

type toolCallBuilder struct {
	id   string
	name strings.Builder
	args strings.Builder
}

// ChatStream 执行流式打字与流式 ToolCalls 聚合调用
func (g *LlamaCppGateway) ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error) {
	httpReq, err := g.buildRequest(ctx, req, true)
	if err != nil {
		return nil, err
	}

	resp, err := g.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("llamacpp: http stream error: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		return nil, fmt.Errorf("llamacpp: stream returned status %d: %s", resp.StatusCode, string(body))
	}

	out := make(chan StreamChunk, 32)

	go func() {
		defer resp.Body.Close()
		defer close(out)

		reader := bufio.NewReader(resp.Body)
		var turnUsage Usage
		toolCallMap := make(map[int]*toolCallBuilder)

		for {
			line, err := reader.ReadString('\n')
			if err != nil {
				if err == io.EOF {
					break
				}
				sendStreamChunk(ctx, out, StreamChunk{Err: fmt.Errorf("llamacpp: stream read error: %w", err)})
				return
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

			var chunkDTO llamaCppStreamChunkDTO
			if err := json.Unmarshal([]byte(data), &chunkDTO); err != nil {
				continue
			}

			if chunkDTO.Usage != nil {
				turnUsage = Usage{
					PromptTokens:     chunkDTO.Usage.PromptTokens,
					CompletionTokens: chunkDTO.Usage.CompletionTokens,
					TotalTokens:      chunkDTO.Usage.TotalTokens,
				}
			}

			if len(chunkDTO.Choices) == 0 {
				continue
			}

			choice := chunkDTO.Choices[0]
			// 1. 发送思考与文本增量
			if choice.Delta.ReasoningContent != "" {
				sendStreamChunk(ctx, out, StreamChunk{ReasoningContent: choice.Delta.ReasoningContent})
			}
			if choice.Delta.Content != "" {
				if !sendStreamChunk(ctx, out, StreamChunk{Delta: choice.Delta.Content}) {
					return
				}
			}

			// 2. 累积流式 tool_calls 碎片
			for _, tc := range choice.Delta.ToolCalls {
				idx := 0
				if tc.Index != nil {
					idx = *tc.Index
				}

				builder, exists := toolCallMap[idx]
				if !exists {
					builder = &toolCallBuilder{}
					toolCallMap[idx] = builder
				}

				if tc.ID != "" {
					builder.id = tc.ID
				}
				if tc.Function.Name != "" {
					builder.name.WriteString(tc.Function.Name)
				}
				if tc.Function.Arguments != "" {
					builder.args.WriteString(tc.Function.Arguments)
				}
			}
		}

		// 聚合完成所有 ToolCalls
		var finalToolCalls []ToolCall
		if len(toolCallMap) > 0 {
			indices := make([]int, 0, len(toolCallMap))
			for idx := range toolCallMap {
				indices = append(indices, idx)
			}
			sort.Ints(indices)

			for _, idx := range indices {
				b := toolCallMap[idx]
				finalToolCalls = append(finalToolCalls, ToolCall{
					ID:        b.id,
					Name:      b.name.String(),
					Arguments: json.RawMessage(b.args.String()),
				})
			}
		}

		if turnUsage.TotalTokens > 0 {
			g.mu.Lock()
			g.totalUsage.Add(turnUsage)
			g.mu.Unlock()
		}

		// 发送结束块
		sendStreamChunk(ctx, out, StreamChunk{
			Done:      true,
			ToolCalls: finalToolCalls,
			Usage:     &turnUsage,
		})
	}()

	return out, nil
}

// GetTotalUsage 获取当前网关实例累计消耗的总 Token 用量
func (g *LlamaCppGateway) GetTotalUsage() Usage {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.totalUsage
}
