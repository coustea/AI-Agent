package llm

import (
	"context"
	"crypto/x509"
	"errors"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

// 429 会退避重试，最终成功
func TestChatStream_RetriesOnRateLimit(t *testing.T) {
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if atomic.AddInt32(&calls, 1) < 3 {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusTooManyRequests)
			_, _ = w.Write([]byte(`{"error":{"message":"rate limited"}}`))
			return
		}
		writeSSE(t, w, `{"choices":[{"delta":{"content":"ok"}}]}`, sseDonePayload)
	}))
	defer srv.Close()

	c := newTestClientWith(t, Config{
		Provider: ProviderDeepSeek,
		BaseURL:  srv.URL,
		APIKey:   "test-key",
		Attempts: 3,
	})
	stream, err := c.ChatStream(t.Context(), Request{Messages: []Message{{Role: RoleUser, Content: "hi"}}})
	if err != nil {
		t.Fatalf("重试后应成功，实际 %v", err)
	}

	deltas, terminal := collect(t, stream)
	if terminal.Finish != StopEnd || terminal.Err != nil {
		t.Fatalf("期望正常结束，实际 finish=%s err=%v", terminal.Finish, terminal.Err)
	}
	if strings.Join(deltas, "") != "ok" {
		t.Errorf("期望收到 ok，实际 %v", deltas)
	}
	if got := atomic.LoadInt32(&calls); got != 3 {
		t.Errorf("期望请求 3 次，实际 %d", got)
	}
}

// 401 属于不可重试错误：只请求一次，且错误里带出上游 message
func TestChatStream_NoRetryOnAuthFailure(t *testing.T) {
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = w.Write([]byte(`{"error":{"message":"invalid api key"}}`))
	}))
	defer srv.Close()

	c := newTestClientWith(t, Config{
		Provider: ProviderDeepSeek,
		BaseURL:  srv.URL,
		APIKey:   "test-key",
		Attempts: 3,
	})
	_, err := c.ChatStream(t.Context(), Request{Messages: []Message{{Role: RoleUser, Content: "hi"}}})
	if err == nil {
		t.Fatalf("期望返回错误")
	}
	if got := atomic.LoadInt32(&calls); got != 1 {
		t.Errorf("401 不应重试，实际请求 %d 次", got)
	}

	var apiErr *APIError
	if !errors.As(err, &apiErr) {
		t.Fatalf("期望 *APIError，实际 %T", err)
	}
	if apiErr.Status != http.StatusUnauthorized || apiErr.Retryable() {
		t.Errorf("401 应不可重试，实际 status=%d retryable=%v", apiErr.Status, apiErr.Retryable())
	}
	if !strings.Contains(err.Error(), "invalid api key") {
		t.Errorf("错误文案应包含上游 message，实际 %s", err.Error())
	}
}

// 错误响应体读取必须限长，避免网关整页 HTML 打爆内存
func TestChatStream_ErrorBodyTruncated(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadGateway)
		_, _ = w.Write([]byte(strings.Repeat("x", maxErrorBodySize*2)))
	}))
	defer srv.Close()

	c := newTestClient(t, srv.URL)
	_, err := c.ChatStream(t.Context(), Request{Messages: []Message{{Role: RoleUser, Content: "hi"}}})
	if err == nil {
		t.Fatalf("期望返回错误")
	}

	var apiErr *APIError
	if !errors.As(err, &apiErr) {
		t.Fatalf("期望 *APIError，实际 %T", err)
	}
	if len(apiErr.Body) > maxErrorBodySize {
		t.Errorf("错误体应被截断到 %d 字节以内，实际 %d", maxErrorBodySize, len(apiErr.Body))
	}
}

// 默认 Transport 必须保留系统代理并启用 HTTP/2 自动协商
func TestNewHTTPClient_ProxyAndHTTP2(t *testing.T) {
	transport, ok := newHTTPClient().Transport.(*http.Transport)
	if !ok {
		t.Fatalf("期望 *http.Transport")
	}
	if transport.Proxy == nil {
		t.Errorf("Proxy 不能为 nil，否则 HTTPS_PROXY 被静默忽略")
	}
	if !transport.ForceAttemptHTTP2 {
		t.Errorf("ForceAttemptHTTP2 必须为 true，否则自定义 Transport 会降级到 HTTP/1.1")
	}
}

// 退避时长必须封顶，且不早于基准值
func TestBackoffDelay_Bounded(t *testing.T) {
	for attempt := 1; attempt <= 12; attempt++ {
		d := backoffDelay(attempt, 0)
		if d > maxBackoff+maxBackoff/4 {
			t.Errorf("attempt %d 退避过长: %v", attempt, d)
		}
		if d < 0 {
			t.Errorf("attempt %d 退避为负: %v", attempt, d)
		}
	}
	if got := backoffDelay(3, time.Second); got != time.Second {
		t.Errorf("上游给出 Retry-After 时应优先采用，实际 %v", got)
	}
	if got := backoffDelay(3, time.Hour); got != maxRetryAfter {
		t.Errorf("Retry-After 应被 maxRetryAfter 截断，实际 %v", got)
	}
}

// 证书错误重试不会自愈，必须判定为不可重试
func TestAPIError_RetryableNotOnCertificateFailure(t *testing.T) {
	err := &APIError{Err: x509.UnknownAuthorityError{}}
	if err.Retryable() {
		t.Errorf("证书校验失败不应重试")
	}
}

// 纯传输层失败（连接重置等）可重试；取消、超时与 DNS NXDOMAIN 不可重试
func TestAPIError_RetryableTransportFailures(t *testing.T) {
	if !(&APIError{Err: errors.New("connection reset")}).Retryable() {
		t.Errorf("普通传输错误应可重试")
	}
	if (&APIError{Err: context.Canceled}).Retryable() {
		t.Errorf("取消不应重试")
	}
	if (&APIError{Err: context.DeadlineExceeded}).Retryable() {
		t.Errorf("超时不应重试")
	}
	if (&APIError{Err: &net.DNSError{Err: "no such host", Name: "nope.invalid", IsNotFound: true}}).Retryable() {
		t.Errorf("DNS NXDOMAIN 不应重试")
	}
}
