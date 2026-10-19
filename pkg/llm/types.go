package llm

import "encoding/json"

// Role 定义大模型对话消息角色
type Role string

const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
	RoleTool      Role = "tool"
)

// ToolDefinition 统一大模型工具描述元信息（支持 Function Calling）
type ToolDefinition struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
}

// ToolCall 统一大模型生成的工具调用指令
type ToolCall struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
}

// ToolResult 统一工具执行完毕后的回灌结果
type ToolResult struct {
	ToolCallID string `json:"tool_call_id"`
	Name       string `json:"name"`
	Content    string `json:"content"`
	IsError    bool   `json:"is_error,omitempty"`
}

// Message 统一对话消息体
type Message struct {
	Role             Role        `json:"role"`
	Content          string      `json:"content,omitempty"`
	ReasoningContent string      `json:"reasoning_content,omitempty"` // 深度思考链（如 DeepSeek R1、星火深度推理）
	ToolCalls        []ToolCall  `json:"tool_calls,omitempty"`
	ToolResult       *ToolResult `json:"tool_result,omitempty"`
}

// ChatRequest 统一大模型调用请求
type ChatRequest struct {
	Model       string           `json:"model,omitempty"`
	Messages    []Message        `json:"messages"`
	Tools       []ToolDefinition `json:"tools,omitempty"`
	Temperature *float32         `json:"temperature,omitempty"`
	MaxTokens   *int             `json:"max_tokens,omitempty"`
}

// ChatResponse 统一大模型流式增量与最终结果块
type ChatResponse struct {
	Delta            string     `json:"delta,omitempty"`             // 增量生成文本
	ReasoningContent string     `json:"reasoning_content,omitempty"` // 增量思考链文本
	ToolCalls        []ToolCall `json:"tool_calls,omitempty"`        // 工具调用结果（流结束时汇总）
	Usage            *Usage     `json:"usage,omitempty"`             // Token 消耗
	Done             bool       `json:"done"`                        // 是否完成
	Err              error      `json:"err,omitempty"`               // 错误信息
}

// Usage 统一 Token 用量统计
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
