// Package tutor 实现 TutorAgent：系统的教学智能体。
//
// 职责划分（这是本包最重要的设计约束）：
//
//	harness.go  运行上下文：加载历史、解析附件、准备工作区、组装消息
//	agent.go    TutorAgent 的构建：模型、工具、Middleware、Skills
//	runtime.go  执行与事件转换：消费 Eino Runner 事件，产出业务事件
//	events.go   面向前端的业务事件定义
//	prompt.md   教学约束
//
// Agent 的推理与工具调用完全交给 Eino ADK 原生的 ReAct 机制，
// 本包不实现任何分类路由、Tool Dispatcher 或手写 ReAct 循环。
package tutor

import "time"

// 业务事件类型。前端按这些类型渲染，变更需同步前端。
const (
	// EventMessage 增量文本
	EventMessage = "message"
	// EventToolStart 工具开始执行
	EventToolStart = "tool_start"
	// EventToolEnd 工具执行结束
	EventToolEnd = "tool_end"
	// EventError 运行错误
	EventError = "error"
	// EventDone 本轮结束
	EventDone = "done"
)

// Event 是 Runtime 输出给传输层的一条业务事件。
//
// 它不是 Eino AgentEvent 的替代品，而是「已经发生在业务层的事实」：
// 文本增量、工具结果、产物引用。转换逻辑集中在 runtime.go，
// 传输层只负责把 Event 编码成 SSE 帧。
type Event struct {
	Type string
	Data any
}

// MessageData 是 EventMessage 的负载。
type MessageData struct {
	// Text 增量文本
	Text string `json:"text"`
	// Reset 为 true 表示清空已渲染内容
	Reset bool `json:"reset,omitempty"`
}

// ToolData 是 EventToolStart / EventToolEnd 的负载。
type ToolData struct {
	Name string `json:"name"`
	// CallID 用于把 start 与 end 配对
	CallID string `json:"call_id,omitempty"`
	// Args 工具入参摘要（start 时给出），已截断
	Args string `json:"args,omitempty"`
	// Result 工具结果摘要（end 时给出），已截断
	Result string `json:"result,omitempty"`
	// ElapsedMS 执行耗时
	ElapsedMS int64 `json:"elapsed_ms,omitempty"`
	// Error 工具执行失败原因
	Error string `json:"error,omitempty"`
}

// ErrorData 是 EventError 的负载。
type ErrorData struct {
	Message string `json:"message"`
	// Retryable 表示重试可能成功（如上游 429）
	Retryable bool `json:"retryable,omitempty"`
}

// DoneData 是 EventDone 的负载。
type DoneData struct {
	// MessageID 落库后的 assistant 消息 ID
	MessageID uint64 `json:"message_id"`
	// Status completed / failed / cancelled
	Status string `json:"status"`
	// ElapsedMS 本轮总耗时
	ElapsedMS int64 `json:"elapsed_ms"`
	// ToolCalls 本轮调用过的工具名，便于前端展示与排障
	ToolCalls []string `json:"tool_calls,omitempty"`
}

// Emitter 接收业务事件。
//
// 返回 error 表示下游写失败（通常是客户端断开），
// Runtime 据此停止执行，避免继续消耗算力。
type Emitter func(Event) error

// emit 安全地调用 Emitter。
func emit(e Emitter, ev Event) error {
	if e == nil {
		return nil
	}
	return e(ev)
}

// truncate 按 rune 截断，用于工具入参与结果的摘要。
func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n]) + "…"
}

// 确保 time 包被使用（耗时统计）。
var _ = time.Second
