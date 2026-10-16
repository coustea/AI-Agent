package protocol

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

// Decision 权限决策枚举
type Decision string

const (
	DecisionAllowOnce    Decision = "allow_once"    // 仅允许本次
	DecisionAllowSession Decision = "allow_session" // 本会话信任同类命令
	DecisionDeny         Decision = "deny"          // 拒绝执行
)

// ToolCallRecord 纯数据工具调用记录
type ToolCallRecord struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
}

// ToolResultRecord 纯数据工具执行结果记录
type ToolResultRecord struct {
	ToolCallID string `json:"tool_call_id"`
	Name       string `json:"name"`
	Content    string `json:"content"`
	IsError    bool   `json:"is_error"`
}

// PermissionRequest 纯数据权限审批请求（彻底消灭闭包，由 RequestID 异步关联）
type PermissionRequest struct {
	RequestID string `json:"request_id"`
	ToolName  string `json:"tool_name"`
	Arguments string `json:"arguments"`
	Reason    string `json:"reason"`
}

// Usage 纯数据 Token 消耗用量统计
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// Event 统一纯数据流式事件（全部字段原生支持 JSON 序列化，跨进程与网络友好）
type Event struct {
	Type       EventType          `json:"type"`
	Delta      string             `json:"delta,omitempty"`
	Reasoning  string             `json:"reasoning,omitempty"`
	ToolCall   *ToolCallRecord    `json:"tool_call,omitempty"`
	ToolResult *ToolResultRecord  `json:"tool_result,omitempty"`
	Permission *PermissionRequest `json:"permission,omitempty"`
	Usage      *Usage             `json:"usage,omitempty"`
	Error      string             `json:"error,omitempty"` // 纯字符串错误说明
}

// ConfigView 暴露给前端只读呈现的配置视图结构体
type ConfigView struct {
	Provider           string   `json:"provider"`
	ModelName          string   `json:"model_name"`
	HasAPIKey          bool     `json:"has_api_key"`
	AvailableProviders []string `json:"available_providers"`
}
