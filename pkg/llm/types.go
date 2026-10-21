package llm

import "encoding/json"

// Role 定义对话消息角色。
type Role string

const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
	RoleTool      Role = "tool"
)

// ToolDefinition 描述一个可被模型调用的工具。
type ToolDefinition struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
}

// ToolCall 是模型生成的一次工具调用指令。
type ToolCall struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
}

// ToolResult 是工具执行完毕后回灌给模型的结果。
type ToolResult struct {
	ToolCallID string `json:"tool_call_id"`
	Name       string `json:"name"`
	Content    string `json:"content"`
	IsError    bool   `json:"is_error,omitempty"`
}

// Message 是统一对话消息体。
// 这里刻意不携带任何协议字段约束：OpenAI wire 格式的映射全部在 protocol.go 完成，
// 因此领域模型不会因为厂商报文细节（content 的 null/"" 三态、reasoning_content 只进不出）被污染。
type Message struct {
	Role             Role        `json:"role"`
	Content          string      `json:"content,omitempty"`
	ReasoningContent string      `json:"reasoning_content,omitempty"`
	ToolCalls        []ToolCall  `json:"tool_calls,omitempty"`
	ToolResult       *ToolResult `json:"tool_result,omitempty"`
}

// Request 是一次大模型调用请求。
// 若 Model 非空，将覆盖 Client 默认绑定的模型。
type Request struct {
	Model       string
	Messages    []Message
	Tools       []ToolDefinition
	Temperature *float32
	MaxTokens   *int
}

// StopReason 说明一次流式调用是如何结束的。
type StopReason string

const (
	StopEnd           StopReason = "end"            // 模型正常收尾
	StopToolCalls     StopReason = "tool_calls"     // 模型要求调用工具
	StopLength        StopReason = "length"         // 触达 max_tokens，回复被截断但内容有效
	StopContentFilter StopReason = "content_filter" // 上游内容策略拦截
	StopCanceled      StopReason = "canceled"       // 调用方取消或超时
	StopTruncated     StopReason = "truncated"      // 上游未给出收尾信号即断开
	StopFailed        StopReason = "failed"         // 传输或协议失败
)

// Clean 报告该终止原因是否代表一次完整、可继续使用的回复。
// 这是 Chunk.Err 是否为 nil 的唯一判据。
func (r StopReason) Clean() bool {
	switch r {
	case StopEnd, StopToolCalls, StopLength, StopContentFilter:
		return true
	}
	return false
}

// Chunk 是流式调用的一个事件。
//
// 四条不变量由 stream.go 的 pump 统一保证：
//  1. 终块（Finish != ""）恰好出现一次，且一定是通道的最后一个元素；
//  2. Err != nil 当且仅当 Finish 不属于 Clean 集合；
//  3. Usage 恒为值类型，终块携带本轮完整用量；
//  4. ToolCalls 只在终块携带，且已按协议分片顺序还原为完整调用。
type Chunk struct {
	Delta            string     // 增量正文
	ReasoningContent string     // 增量思考链
	ToolCalls        []ToolCall // 仅终块携带
	Usage            Usage      // 仅终块有效
	Finish           StopReason // 仅终块非空
	Err              error      // 仅异常终止时非 nil
}

// Terminal 报告该事件是否为终块。
func (c Chunk) Terminal() bool { return c.Finish != "" }

// Usage 是 Token 用量统计。
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// Add 累加用量。
func (u *Usage) Add(other Usage) {
	u.PromptTokens += other.PromptTokens
	u.CompletionTokens += other.CompletionTokens
	u.TotalTokens += other.TotalTokens
}
