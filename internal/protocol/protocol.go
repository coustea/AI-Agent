package protocol

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

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

// ============================================================================
// 全系统统一结构化链路审计与追踪契约 (Trace DTOs)
// ============================================================================

// TraceEvent 记录全系统单次结构化执行链路事件，支持 100% 原始数据格式化为完整 JSON
type TraceEvent struct {
	Step      int           `json:"step"`               // 所属 ReAct 步骤 (-1 为全局轮次事件)
	Type      string        `json:"type"`               // "turn_start", "llm_req", "llm_resp", "tool_start", "tool_end", "turn_end"
	Title     string        `json:"title"`              // 列表摘要标题
	Timestamp time.Time     `json:"timestamp"`          // 记录时间戳
	Duration  time.Duration `json:"duration,omitempty"` // 耗时 (若有)
	Payload   any           `json:"payload"`            // 原始结构体数据对象 (如 LLMRequestTrace, ToolTrace 等)
}

// PrettyJSON 将 Payload 格式化为 2 格缩进的完整 JSON 字符串，保留所有真实字段与参数
func (e TraceEvent) PrettyJSON() string {
	b, err := json.MarshalIndent(e.Payload, "", "  ")
	if err != nil {
		return fmt.Sprintf("{\n  \"error\": %q\n}", err.Error())
	}
	return string(b)
}

// LLMRequestTrace 记录向大模型发送的完整请求快照
type LLMRequestTrace struct {
	Step         int              `json:"step"`
	Provider     string           `json:"provider"`
	ModelName    string           `json:"model_name"`
	SystemPrompt string           `json:"system_prompt"`
	Messages     []Message        `json:"messages"`
	Tools        []ToolDefinition `json:"tools"`
	Timestamp    time.Time        `json:"timestamp"`
}

// LLMResponseTrace 记录大模型返回的完整决策快照
type LLMResponseTrace struct {
	Step             int           `json:"step"`
	Duration         time.Duration `json:"duration"`
	Reply            string        `json:"reply"`
	ReasoningContent string        `json:"reasoning_content,omitempty"`
	ToolCalls        []ToolCall    `json:"tool_calls,omitempty"`
	Usage            *Usage        `json:"usage,omitempty"`
	Error            error         `json:"error,omitempty"`
}

// ToolTrace 记录工具执行前后的完整快照
type ToolTrace struct {
	Step      int           `json:"step"`
	Call      ToolCall      `json:"call"`
	Result    ToolResult    `json:"result"`
	Duration  time.Duration `json:"duration"`
	Timestamp time.Time     `json:"timestamp"`
}

// TurnSummaryTrace 记录一轮完整问答的汇总快照
type TurnSummaryTrace struct {
	TurnID     string        `json:"turn_id"`
	Prompt     string        `json:"prompt"`
	TotalSteps int           `json:"total_steps"`
	TotalUsage Usage         `json:"total_usage"`
	Duration   time.Duration `json:"duration"`
	Success    bool          `json:"success"`
	Error      error         `json:"error,omitempty"`
}

// ============================================================================
// 智能体核心对外纯虚接口 (Agent Contract)
// ============================================================================

// Agent 定义智能体调用的对外核心契约，任何前端（TUI、桌面端、无头宿主）直接依赖该接口
type Agent interface {
	// Run 开启单轮对话交互，返回原生支持序列化的纯数据事件流
	Run(ctx context.Context, prompt string) (<-chan Event, error)

	// RespondPermission 异步审批权限请求（基于 requestID 关联）
	RespondPermission(requestID string, decision Decision) error

	// Reset 清空当前会话记忆
	Reset()

	// Config 获取当前配置与就绪状态（只读视图）
	Config() ConfigView

	// UpdateConfig 更新模型提供商、密钥与模型名称（内核负责落盘 config.json 与热切网关）
	UpdateConfig(provider, apiKey, model string) error

	// MemoryCount 返回当前工作区生效的长期记忆篇数
	MemoryCount() int

	// WorkDir 获取当前绑定的工作目录
	WorkDir() string

	// Traces 返回当前/最近一轮对话的完整详细结构化追踪事件切片
	Traces() []TraceEvent
}
