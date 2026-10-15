package gateway

import (
	"context"
	"encoding/json"
	"errors"
)

var (
	ErrEmptyAPIKey   = errors.New("gateway: api key cannot be empty")
	ErrEmptyMessages = errors.New("gateway: messages cannot be empty")
)

// Role 统一角色类型
type Role string

const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
	RoleTool      Role = "tool"
)

// ToolDefinition 暴露给大模型的工具 JSON Schema 描述
type ToolDefinition struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
}

// ToolCall 模型决定调用的工具指令
type ToolCall struct {
	ID        string          `json:"id"`
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

// ToolResult 工具执行后回传给模型的观察结果
type ToolResult struct {
	ToolCallID string `json:"tool_call_id"`
	Name       string `json:"name"`
	Content    string `json:"content"`
	IsError    bool   `json:"is_error,omitempty"`
}

// Message 统一消息结构
type Message struct {
	Role             Role        `json:"role"`
	Content          string      `json:"content,omitempty"`
	ReasoningContent string      `json:"reasoning_content,omitempty"`
	ToolCalls        []ToolCall  `json:"tool_calls,omitempty"`
	ToolResult       *ToolResult `json:"tool_result,omitempty"`
}

// Usage 统一记录 Token 用量
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// Add 累加用量
func (u *Usage) Add(other Usage) {
	u.PromptTokens += other.PromptTokens
	u.CompletionTokens += other.CompletionTokens
	u.TotalTokens += other.TotalTokens
}

// ChatRequest 统一大模型对话请求参数
type ChatRequest struct {
	Model       string           `json:"model,omitempty"`
	Messages    []Message        `json:"messages"`
	Tools       []ToolDefinition `json:"tools,omitempty"`
	Temperature *float32         `json:"temperature,omitempty"`
	MaxTokens   *int             `json:"max_tokens,omitempty"`
}

// ChatResponse 统一单次对话完整响应
type ChatResponse struct {
	Content   string     `json:"content"`
	ToolCalls []ToolCall `json:"tool_calls,omitempty"`
	Usage     Usage      `json:"usage"`
}

// StreamChunk 统一流式输出块
type StreamChunk struct {
	Delta            string     `json:"delta,omitempty"`
	ReasoningContent string     `json:"reasoning_content,omitempty"`
	ToolCalls        []ToolCall `json:"tool_calls,omitempty"`
	Usage            *Usage     `json:"usage,omitempty"`
	Done             bool       `json:"done"`
	Err              error      `json:"err,omitempty"`
}

// Gateway 统一 AI 网关接口
type Gateway interface {
	// Chat 执行非流式同步对话调用
	Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error)

	// ChatStream 执行流式调用，逐个 chunk 返回生成内容
	ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error)

	// TotalUsage 获取当前网关实例累计消耗的总 Token 用量
	TotalUsage() Usage
}
