package protocol

import "encoding/json"

// Role 统一消息角色类型
type Role string

const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
	RoleTool      Role = "tool"
)

// ToolDefinition 暴露给大模型的工具 JSON Schema 描述元信息
type ToolDefinition struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
}

// ToolCall 统一大模型发出的工具调用指令 (Gateway、Agent、Tool、TUI 通用)
type ToolCall struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Arguments string `json:"arguments"` // 统一为规范 JSON 字符串，跨语言与跨端最友好
}

// ToolResult 统一工具执行后的观察回灌结果 (Tool、Agent、Memory、TUI 通用)
type ToolResult struct {
	ToolCallID string `json:"tool_call_id"`
	Name       string `json:"name"`
	Content    string `json:"content"`
	IsError    bool   `json:"is_error,omitempty"`
}

// Message 统一多轮对话消息结构体
type Message struct {
	Role             Role        `json:"role"`
	Content          string      `json:"content,omitempty"`
	ReasoningContent string      `json:"reasoning_content,omitempty"`
	ToolCalls        []ToolCall  `json:"tool_calls,omitempty"`
	ToolResult       *ToolResult `json:"tool_result,omitempty"`
}

// ChatRequest 统一大模型交互请求
type ChatRequest struct {
	Model       string           `json:"model,omitempty"`
	Messages    []Message        `json:"messages"`
	Tools       []ToolDefinition `json:"tools,omitempty"`
	Temperature *float32         `json:"temperature,omitempty"`
	MaxTokens   *int             `json:"max_tokens,omitempty"`
}

// ChatResponse 统一大模型响应块 (兼容流式增量与最终汇总)
type ChatResponse struct {
	Delta            string     `json:"delta,omitempty"`
	ReasoningContent string     `json:"reasoning_content,omitempty"`
	ToolCalls        []ToolCall `json:"tool_calls,omitempty"`
	Usage            *Usage     `json:"usage,omitempty"`
	Done             bool       `json:"done"`
	Err              error      `json:"err,omitempty"`
}

// Usage 统一 Token 消耗用量统计
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

// Decision 统一权限决策枚举
type Decision string

const (
	DecisionAllowOnce    Decision = "allow_once"    // 仅允许本次
	DecisionAllowSession Decision = "allow_session" // 本会话信任同类命令
	DecisionDeny         Decision = "deny"          // 拒绝执行
)

// PermissionRequest 统一权限审批请求 (Permission Manager、Agent、TUI 通用)
type PermissionRequest struct {
	RequestID  string `json:"request_id,omitempty"`
	ToolCallID string `json:"tool_call_id,omitempty"`
	ToolName   string `json:"tool_name"`
	Arguments  string `json:"arguments"`
	WorkDir    string `json:"work_dir,omitempty"`
	Reason     string `json:"reason"`
}

// EventType 定义流式事件的类型枚举
type EventType string

const (
	EventDelta          EventType = "delta"           // 文本输出增量
	EventReasoningDelta EventType = "reasoning_delta" // 深度思考链增量 (DeepSeek 等)
	EventToolCallStart  EventType = "tool_start"      // 工具开始调用
	EventToolCallResult EventType = "tool_result"     // 工具执行完成
	EventPermissionReq  EventType = "permission_req"  // 触发安全策略，请求人工审批
	EventDone           EventType = "done"            // 对话完成
	EventError          EventType = "error"           // 对话异常终止
)

// Event 统一纯数据流式事件 (原生无损复用 ToolCall / ToolResult / Usage / PermissionRequest)
type Event struct {
	Type       EventType          `json:"type"`
	Delta      string             `json:"delta,omitempty"`
	Reasoning  string             `json:"reasoning,omitempty"`
	ToolCall   *ToolCall          `json:"tool_call,omitempty"`   // 直接使用统一的 ToolCall
	ToolResult *ToolResult        `json:"tool_result,omitempty"` // 直接使用统一的 ToolResult
	Permission *PermissionRequest `json:"permission,omitempty"`  // 直接使用统一的 PermissionRequest
	Usage      *Usage             `json:"usage,omitempty"`       // 直接使用统一的 Usage
	Error      string             `json:"error,omitempty"`       // 纯字符串错误说明
}

// ProviderInfo 暴露给前端只读呈现的平台状态与推荐模型（纯数据契约，无业务逻辑）
type ProviderInfo struct {
	ID                string   `json:"id"`                 // 厂商标识 (如 "gemini", "deepseek", "llamacpp", "spark")
	Name              string   `json:"name"`               // 友好展示名称 (如 "Google Gemini", "DeepSeek", "llama.cpp", "讯飞星辰 MaaS")
	Description       string   `json:"description"`        // 简短能力说明与端点提示
	IsLocal           bool     `json:"is_local"`           // 是否为本地免密钥服务
	IsConfigured      bool     `json:"is_configured"`      // 是否已配置就绪 (已存 Key 或本地服务)
	CurrentModel      string   `json:"current_model"`      // 当前或最近使用的模型
	RecommendedModels []string `json:"recommended_models"` // 常用预设推荐模型清单
}

// ConfigView 暴露给前端只读呈现的配置视图结构体
type ConfigView struct {
	Provider           string         `json:"provider"`
	ModelName          string         `json:"model_name"`
	HasAPIKey          bool           `json:"has_api_key"`
	AvailableProviders []string       `json:"available_providers"`
	Providers          []ProviderInfo `json:"providers,omitempty"`
}
