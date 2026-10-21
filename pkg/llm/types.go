package llm

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/http"
	"strings"
	"time"
)

// ============================================================================
// 对话核心模型
// ============================================================================

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
// 这里不携带任何底层协议字段约束：OpenAI wire 格式的映射由 stream.go 统一完成。
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

// ============================================================================
// 响应与事件模型
// ============================================================================

// StopReason 说明一次调用是如何结束的。
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
func (r StopReason) Clean() bool {
	switch r {
	case StopEnd, StopToolCalls, StopLength, StopContentFilter:
		return true
	}
	return false
}

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

// Chunk 是流式调用的一个事件。
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

// ============================================================================
// 客户端配置
// ============================================================================

// Config 是创建 Client 的全部输入。
// 基于标准 OpenAI 协议，仅需提供 BaseURL、APIKey 与 Model 即可接入任意兼容服务。
type Config struct {
	BaseURL    string        // 服务根地址（自动自适应补齐 /chat/completions）
	APIKey     string        // API 密钥（本地免密服务可为空）
	Model      string        // 默认模型名（单次 Request.Model 可覆盖）
	HTTPClient *http.Client  // 空 = 内置优化传输层客户端
	Timeout    time.Duration // 空 = 10 分钟（整次调用硬超时）
	Attempts   int           // 0 = 默认 3 次；1 = 不重试
}

// ============================================================================
// 错误定义
// ============================================================================

var (
	// ErrEmptyBaseURL 表示未提供服务地址。
	ErrEmptyBaseURL = errors.New("llm: 未提供 BaseURL")
	// ErrEmptyModel 表示未指定模型名称。
	ErrEmptyModel = errors.New("llm: 未指定模型名称")
	// ErrEmptyMessages 表示请求没有携带任何消息。
	ErrEmptyMessages = errors.New("llm: 消息列表为空")
	// ErrStreamIncomplete 表示通道已关闭但从未收到终块（内部不变量被破坏）。
	ErrStreamIncomplete = errors.New("llm: 流未收到终止块")
	// ErrStreamTruncated 表示上游在给出收尾信号前断开。
	ErrStreamTruncated = errors.New("llm: 上游在回复完成前断开连接")
	// ErrProtocolViolation 表示上游返回了无法解析的数据帧。
	ErrProtocolViolation = errors.New("llm: 无法解析的上游数据")
)

// APIError 是一次非 2xx 响应或传输失败的结构化描述。
type APIError struct {
	URL        string
	Status     int           // 0 表示未拿到响应（传输层失败）
	Body       string        // 已截断的响应体
	RetryAfter time.Duration // 0 表示上游未给出
	Err        error         // 传输层原始错误
}

// Error 生成可直接展示给用户的错误文案，优先透出上游的 error.message。
func (e *APIError) Error() string {
	var b strings.Builder
	b.WriteString("llm: ")
	if e.Status > 0 {
		fmt.Fprintf(&b, "HTTP %d", e.Status)
	} else {
		b.WriteString("请求失败")
	}
	if e.URL != "" {
		fmt.Fprintf(&b, " (%s)", e.URL)
	}
	if msg := extractErrorMessage(e.Body); msg != "" {
		fmt.Fprintf(&b, ": %s", msg)
	} else if e.Err != nil {
		fmt.Fprintf(&b, ": %v", e.Err)
	}
	return b.String()
}

// Unwrap 暴露底层传输错误，便于 errors.Is/As 判断。
func (e *APIError) Unwrap() error { return e.Err }

// Retryable 判断该错误是否值得重试。
// 取消、超时、证书类错误与 DNS NXDOMAIN 一律不重试。
func (e *APIError) Retryable() bool {
	if e.Err != nil {
		if errors.Is(e.Err, context.Canceled) || errors.Is(e.Err, context.DeadlineExceeded) {
			return false
		}
		var dnsErr *net.DNSError
		if errors.As(e.Err, &dnsErr) && dnsErr.IsNotFound {
			return false
		}
		var certErr *tls.CertificateVerificationError
		var unkAuth x509.UnknownAuthorityError
		var hostErr x509.HostnameError
		var certInv x509.CertificateInvalidError
		if errors.As(e.Err, &certErr) || errors.As(e.Err, &unkAuth) || errors.As(e.Err, &hostErr) || errors.As(e.Err, &certInv) {
			return false
		}
	}

	switch {
	case e.Status == 0:
		// 纯传输层失败（连接被重置、临时 DNS 失败等）
		return true
	case e.Status == http.StatusRequestTimeout,
		e.Status == http.StatusConflict,
		e.Status == http.StatusTooManyRequests:
		return true
	case e.Status >= 500:
		return true
	}
	return false
}
