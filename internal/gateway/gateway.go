package gateway

import (
	"context"
	"encoding/json"
	"errors"
)

var (
	ErrNotImplemented = errors.New("gateway: provider not implemented yet")
	ErrEmptyAPIKey    = errors.New("gateway: api key cannot be empty")
	ErrEmptyMessages  = errors.New("gateway: messages cannot be empty")
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
	Parameters  json.RawMessage `json:"parameters"` // 标准 JSON Schema 对象
}

// ToolCall 模型决定调用的工具指令（必须是已完整聚合、参数为合法 JSON 的调用）
type ToolCall struct {
	ID        string          `json:"id"`
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

// ToolResult 工具执行后回传给模型的观察结果（Observation）
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
	ReasoningContent string      `json:"reasoning_content,omitempty"` // 深度思考链/推导内容
	ToolCalls        []ToolCall  `json:"tool_calls,omitempty"`        // RoleAssistant 发起工具调用时携带
	ToolResult       *ToolResult `json:"tool_result,omitempty"`       // RoleTool 回传执行结果时携带
}

// Usage 统一记录每次请求与累计的 Token 用量
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`     // 提问/输入消耗的 Token 数
	CompletionTokens int `json:"completion_tokens"` // 模型输出/回答消耗的 Token 数
	TotalTokens      int `json:"total_tokens"`      // 总计消耗的 Token 数
}

// Add 累加用量
func (u *Usage) Add(other Usage) {
	u.PromptTokens += other.PromptTokens
	u.CompletionTokens += other.CompletionTokens
	u.TotalTokens += other.TotalTokens
}

// ChatRequest 统一大模型对话请求参数
type ChatRequest struct {
	Model       string           `json:"model,omitempty"`       // 若不传则使用提供商默认模型
	Messages    []Message        `json:"messages"`              // 上下文对话历史
	Tools       []ToolDefinition `json:"tools,omitempty"`       // 可用工具定义列表
	Temperature *float32         `json:"temperature,omitempty"` // 采样温度
	MaxTokens   *int             `json:"max_tokens,omitempty"`  // 最大输出 token 限制
}

// ChatResponse 统一单次对话完整响应
type ChatResponse struct {
	Content   string     `json:"content"`              // 回答文本内容
	ToolCalls []ToolCall `json:"tool_calls,omitempty"` // 工具调用指令列表
	Usage     Usage      `json:"usage"`                // 本次请求消耗的 Token 统计
}

// StreamChunk 统一流式打字输出块
type StreamChunk struct {
	Delta            string     `json:"delta,omitempty"`             // 本次增量文本
	ReasoningContent string     `json:"reasoning_content,omitempty"` // 深度思考链增量
	ToolCalls        []ToolCall `json:"tool_calls,omitempty"`        // 完整聚合的 ToolCalls
	Usage            *Usage     `json:"usage,omitempty"`             // 结束块带上的 Token 统计信息
	Done             bool       `json:"done"`                        // 是否输出完毕
	Err              error      `json:"err,omitempty"`               // 遇到的异常错误
}

// Gateway 统一 AI 网关接口契约
type Gateway interface {
	// Chat 执行非流式同步对话调用
	Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error)

	// ChatStream 执行流式打字调用，逐个 chunk 返回生成内容
	ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error)

	// GetTotalUsage 获取当前网关实例累计消耗的总 Token 用量
	GetTotalUsage() Usage
}

func sendStreamChunk(ctx context.Context, ch chan<- StreamChunk, chunk StreamChunk) bool {
	select {
	case ch <- chunk:
		return true
	case <-ctx.Done():
		return false
	}
}
