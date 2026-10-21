package protocol

import (
	"context"
	"time"

	"my-agent/pkg/llm"
)

// LLM 定义大模型统一流式调用接口 (由 pkg/llm.Client 原生实现)。
// 用量统计只由 Agent 侧记录一处，客户端保持无状态。
type LLM interface {
	ChatStream(ctx context.Context, req llm.Request) (<-chan llm.Chunk, error)
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
	ToolCall   *llm.ToolCall      `json:"tool_call,omitempty"`   // 直接使用 llm.ToolCall
	ToolResult *llm.ToolResult    `json:"tool_result,omitempty"` // 直接使用 llm.ToolResult
	Permission *PermissionRequest `json:"permission,omitempty"`  // 直接使用统一的 PermissionRequest
	Usage      *llm.Usage         `json:"usage,omitempty"`       // 直接使用 llm.Usage
	Error      string             `json:"error,omitempty"`       // 纯字符串错误说明
}

// ConfigView 暴露给前端只读呈现的配置视图结构体
type ConfigView struct {
	BaseURL   string `json:"base_url"`
	ModelName string `json:"model_name"`
	HasAPIKey bool   `json:"has_api_key"`
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

// LLMRequestTrace 记录向大模型发送的完整请求快照
type LLMRequestTrace struct {
	Step         int                  `json:"step"`
	BaseURL      string               `json:"base_url"`
	ModelName    string               `json:"model_name"`
	SystemPrompt string               `json:"system_prompt"`
	Messages     []llm.Message        `json:"messages"`
	Tools        []llm.ToolDefinition `json:"tools"`
	Timestamp    time.Time            `json:"timestamp"`
}

// LLMResponseTrace 记录大模型返回的完整决策快照
type LLMResponseTrace struct {
	Step             int            `json:"step"`
	Duration         time.Duration  `json:"duration"`
	Reply            string         `json:"reply"`
	ReasoningContent string         `json:"reasoning_content,omitempty"`
	ToolCalls        []llm.ToolCall `json:"tool_calls,omitempty"`
	Usage            *llm.Usage     `json:"usage,omitempty"`
	Error            error          `json:"error,omitempty"`
}

// ToolTrace 记录工具执行前后的完整快照
type ToolTrace struct {
	Step      int            `json:"step"`
	Call      llm.ToolCall   `json:"call"`
	Result    llm.ToolResult `json:"result"`
	Duration  time.Duration  `json:"duration"`
	Timestamp time.Time      `json:"timestamp"`
}

// TurnSummaryTrace 记录一轮完整问答的汇总快照
type TurnSummaryTrace struct {
	TurnID     string        `json:"turn_id"`
	Prompt     string        `json:"prompt"`
	TotalSteps int           `json:"total_steps"`
	TotalUsage llm.Usage     `json:"total_usage"`
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

	// UpdateConfig 更新端点、密钥与模型名称（内核负责落盘 config.json 并热切客户端）
	UpdateConfig(baseURL, apiKey, model string) error

	// MemoryCount 返回当前工作区生效的长期记忆篇数
	MemoryCount() int

	// WorkDir 获取当前绑定的工作目录
	WorkDir() string
}
