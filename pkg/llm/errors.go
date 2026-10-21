package llm

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"errors"
	"fmt"
	"net"
	"net/http"
	"strings"
	"time"
)

var (
	// ErrNoAPIKey 表示远程厂商缺少凭据。上层据此装配"未就绪内核"。
	ErrNoAPIKey = errors.New("llm: 未提供 API Key")
	// ErrUnknownProvider 表示厂商标识无法识别，不再静默回落到本地厂商。
	ErrUnknownProvider = errors.New("llm: 未知厂商")
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
	Provider   Provider
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
	b.WriteString(string(e.Provider))
	if e.Status > 0 {
		fmt.Fprintf(&b, " 返回 HTTP %d", e.Status)
	} else {
		b.WriteString(" 请求失败")
	}
	if e.URL != "" {
		fmt.Fprintf(&b, " (%s)", e.URL)
	}
	if msg := errorMessage(e.Body); msg != "" {
		fmt.Fprintf(&b, ": %s", msg)
	} else if e.Err != nil {
		fmt.Fprintf(&b, ": %v", e.Err)
	}
	return b.String()
}

// Unwrap 暴露底层传输错误，便于 errors.Is/As 判断。
func (e *APIError) Unwrap() error { return e.Err }

// Retryable 判断该错误是否值得重试。
// 取消、超时、证书类错误与 DNS NXDOMAIN 一律不重试——它们不会因为等待而自愈。
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
		if errors.As(e.Err, &certErr) {
			return false
		}
		var unknownAuthority x509.UnknownAuthorityError
		if errors.As(e.Err, &unknownAuthority) {
			return false
		}
		var hostname x509.HostnameError
		if errors.As(e.Err, &hostname) {
			return false
		}
		var invalid x509.CertificateInvalidError
		if errors.As(e.Err, &invalid) {
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
