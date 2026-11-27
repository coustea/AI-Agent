// Package agent 的运行时对外协议、身份边界与错误分类。
//
// 职责：
//   - 定义 Agent 与 Service / Handler 之间的只读展示契约（Event、Result、CompactionResult、Emitter）；
//   - 维护单次运行的零信任身份上下文 Principal（唯一事实源，包内所有工具、沙箱与 Guard 直接读取）；
//   - 统一运行终态归结（resolveStatus）与用户可读错误脱敏（userFacingError / isTransient）。
//
// 架构约束：
//   - Event 仅用于 SSE 前端展示；历史恢复与持久化始终使用 Eino 原生 *schema.Message。
//   - Principal 仅允许由 Run() 在入口写入 context，任何工具都禁止从模型参数信任 userID / conversationID / workspace。
package agent

import (
	"context"
	"errors"
	"strings"
	"time"

	"github.com/cloudwego/eino/schema"
)

// SSE 展示事件类型与最终运行状态常量，与前端契约严格对齐。
const (
	EventMessage   = "message"
	EventToolStart = "tool_start"
	EventToolEnd   = "tool_end"
	EventError     = "error"
	EventDone      = "done"

	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCancelled = "cancelled"
)

// 包内共享的哨兵错误：
//   - ErrUnavailable 暴露给调用方判断是否降级；
//   - errEmptyAgentOutput / errNoPrincipal 属于运行控制与身份边界；
//   - errToolDenied / errContextBudget / errContextCompaction 供同包中间件与错误分类共享。
var (
	ErrUnavailable       = errors.New("对话能力未启用")
	errEmptyAgentOutput  = errors.New("Agent 未返回最终结果")
	errNoPrincipal       = errors.New("runtime: 缺少已认证用户上下文")
	errToolDenied        = errors.New("工具调用被拒绝")
	errContextBudget     = errors.New("上下文预算不足")
	errContextCompaction = errors.New("自动摘要失败")
)

// Event 是交给上层（Handler/Service）的 SSE 展示事件；不替代持久化用的原生消息。
type Event struct {
	Type string
	Data any
}

// MessageData 的 Text 为增量正文；Reset=true 指示前端撤回本轮已展示的临时正文
// （当模型在吐出部分文字后决定调用工具、或框架触发空响应重试时发生）。
type MessageData struct {
	Text  string `json:"text"`
	Reset bool   `json:"reset,omitempty"`
}

// ToolData 通过 CallID 关联同一工具的开始与结束，支持并行或多次调用同名工具。
type ToolData struct {
	Name      string `json:"name"`
	CallID    string `json:"call_id,omitempty"`
	Args      string `json:"args,omitempty"`
	Result    string `json:"result,omitempty"`
	ElapsedMS int64  `json:"elapsed_ms,omitempty"`
}

// ErrorData 向前端传达已脱敏的失败说明与是否建议重试。
type ErrorData struct {
	Message   string `json:"message"`
	Retryable bool   `json:"retryable,omitempty"`
}

// DoneData 由 Service 在数据库落盘完成后发送，携带最终落库的 MessageID 与状态。
type DoneData struct {
	MessageID uint64   `json:"message_id"`
	Status    string   `json:"status"`
	ElapsedMS int64    `json:"elapsed_ms"`
	ToolCalls []string `json:"tool_calls,omitempty"`
}

// Emitter 由调用方注入；返回非 nil 错误（如 SSE 断连）时，Agent 必须立即停止消费。
type Emitter func(Event) error

// CompactionResult 是上下文压缩成功后生成的检查点候选，
// 由 Service 在保存本轮原始 Transcript 时原子推进覆盖边界。
type CompactionResult struct {
	Messages []*schema.Message
	// CoveredTranscriptCount 记录生成检查点时已消费的原始 Transcript 条数，
	// 下轮恢复时只回放该边界之后的新消息，避免重复注入已被摘要覆盖的内容。
	CoveredTranscriptCount int
}

// Result 汇总单轮执行产物：最终答复、未裁剪的原始工具记录、可选摘要检查点与耗时。
type Result struct {
	Message    *schema.Message
	Status     string
	MessageID  uint64
	ToolCalls  []string
	Transcript []*schema.Message // 始终保留工具调用与结果原文，不用运行期裁剪后的视图替代。
	Compaction *CompactionResult
	Elapsed    time.Duration
	runErr     error
}

// Principal 是一次运行的租户身份与物理工作区根目录，仅通过 context 单向传递。
type Principal struct {
	UserID         string
	ConversationID string
	Workspace      string
}

type principalKey struct{}

// withPrincipal 在运行入口注入已鉴权身份；后续文件沙箱、Shell 与业务工具均从同一 ctx 读取。
func withPrincipal(ctx context.Context, p Principal) context.Context {
	return context.WithValue(ctx, principalKey{}, p)
}

// PrincipalFrom 提取已鉴权身份；缺失或 UserID 为空时立即返回 errNoPrincipal（不可恢复致命错误）。
func PrincipalFrom(ctx context.Context) (Principal, error) {
	p, ok := ctx.Value(principalKey{}).(Principal)
	if !ok || strings.TrimSpace(p.UserID) == "" {
		return Principal{}, errNoPrincipal
	}
	return p, nil
}

// resolveStatus 归结最终状态：若中断前已有部分正文则保留，否则回填取消/失败提示文案。
func resolveStatus(answer string, runErr error, ctx context.Context) (status, content string) {
	if errors.Is(runErr, context.Canceled) || errors.Is(ctx.Err(), context.Canceled) {
		if strings.TrimSpace(answer) == "" {
			answer = "[本轮生成已停止]"
		}
		return StatusCancelled, answer
	}
	if runErr == nil && ctx.Err() == nil {
		return StatusCompleted, answer
	}
	if runErr == nil {
		runErr = ctx.Err()
	}
	if strings.TrimSpace(answer) == "" {
		answer = userFacingError(runErr)
	}
	return StatusFailed, answer
}

// userFacingError 将内部技术错误映射为面向用户的中文提示，避免泄露宿主机路径或堆栈细节。
func userFacingError(err error) string {
	if err == nil {
		return ""
	}
	msg := err.Error()
	switch {
	case errors.Is(err, context.DeadlineExceeded):
		return "本轮生成超时，请重试"
	case errors.Is(err, context.Canceled):
		return "生成已取消"
	case errors.Is(err, ErrUnavailable):
		return "对话能力未启用"
	case errors.Is(err, errContextCompaction):
		return "上下文摘要失败，已保留原有对话，请重试"
	case errors.Is(err, errContextBudget):
		return "当前内容超出模型上下文容量，请缩小单次请求或工具输出"
	case errors.Is(err, errEmptyAgentOutput):
		return "Agent 未返回最终结果，请检查工作区文件或重试"
	case strings.Contains(msg, "failed to unmarshal arguments"):
		return "工具参数格式有误，请重试（通常是内容过长或含特殊字符）"
	case strings.Contains(msg, "failed to stream tool call"), strings.Contains(msg, "failed to invoke tool"):
		return "工具调用失败，请重试"
	case isTransient(err):
		return "上游服务暂时不可用，请重试"
	default:
		return "生成失败，请稍后重试"
	}
}

// isTransient 仅用于前端展示 Retryable 标记；本系统严禁对模型/网络错误自动重试。
func isTransient(err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, ErrStreamIdleTimeout) {
		return true
	}
	msg := strings.ToLower(err.Error())
	for _, kw := range []string{
		"429", "500", "502", "503", "504",
		"timeout", "timed out", "deadline",
		"connection reset", "connection refused", "broken pipe",
		"temporarily unavailable", "overloaded", "rate limit", "eof",
	} {
		if strings.Contains(msg, kw) {
			return true
		}
	}
	return false
}

func emit(e Emitter, ev Event) error {
	if e == nil {
		return nil
	}
	return e(ev)
}
