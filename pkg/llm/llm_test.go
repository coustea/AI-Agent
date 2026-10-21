package llm

import (
	"context"
	"crypto/tls"
	"errors"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
)

func newTestClient(t *testing.T, url string) *Client {
	t.Helper()
	c, err := New(Config{
		BaseURL:  url,
		APIKey:   "test-key",
		Model:    "test-model",
		Attempts: 1,
	})
	if err != nil {
		t.Fatalf("构造客户端失败: %v", err)
	}
	return c
}

func TestNew_Validation(t *testing.T) {
	// 空 BaseURL 报错
	if _, err := New(Config{}); !errors.Is(err, ErrEmptyBaseURL) {
		t.Errorf("空 BaseURL 应返回 ErrEmptyBaseURL，实际: %v", err)
	}

	// 正常构造与默认值
	c, err := New(Config{
		BaseURL: "https://api.openai.com/v1",
		APIKey:  "sk-test",
		Model:   "gpt-4o",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.BaseURL() != "https://api.openai.com/v1" {
		t.Errorf("BaseURL 错误: %s", c.BaseURL())
	}
	if c.Model() != "gpt-4o" {
		t.Errorf("Model 错误: %s", c.Model())
	}
	if c.Endpoint() != "https://api.openai.com/v1/chat/completions" {
		t.Errorf("Endpoint 错误: %s", c.Endpoint())
	}
	if c.attempts != defaultAttempts {
		t.Errorf("默认重试次数错误: %d", c.attempts)
	}
	if c.timeout != defaultStreamTimeout {
		t.Errorf("默认超时错误: %v", c.timeout)
	}
}

func TestResolveEndpoint(t *testing.T) {
	cases := []struct {
		input string
		want  string
	}{
		{"https://api.openai.com", "https://api.openai.com/v1/chat/completions"},
		{"https://api.openai.com/", "https://api.openai.com/v1/chat/completions"},
		{"https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"},
		{"https://api.openai.com/v1/", "https://api.openai.com/v1/chat/completions"},
		{"https://api.openai.com/v1/chat/completions", "https://api.openai.com/v1/chat/completions"},
		{"https://generativelanguage.googleapis.com/v1beta/openai", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"},
		{"https://maas-api.cn-huabei-1.xf-yun.com/v2", "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions"},
		{"http://127.0.0.1:11434", "http://127.0.0.1:11434/v1/chat/completions"},
	}

	for _, tc := range cases {
		got := resolveEndpoint(tc.input)
		if got != tc.want {
			t.Errorf("resolveEndpoint(%q) = %q, want %q", tc.input, got, tc.want)
		}
	}
}

func TestClient_Chat_Unary(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test-key" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"reasoning_content\":\"thinking...\"}}]}\n\n")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"Hello, \"}}]}\n\n")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"World!\"},\"finish_reason\":\"stop\"}],\"usage\":{\"total_tokens\":15}}\n\n")
		_, _ = io.WriteString(w, "data: [DONE]\n\n")
	}))
	defer server.Close()

	client := newTestClient(t, server.URL)
	chunk, err := client.Chat(context.Background(), Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("Chat 失败: %v", err)
	}
	if chunk.Delta != "Hello, World!" {
		t.Errorf("Chat 正文累加错误，期望 'Hello, World!'，实际 %q", chunk.Delta)
	}
	if chunk.ReasoningContent != "thinking..." {
		t.Errorf("Chat 思考链错误，期望 'thinking...'，实际 %q", chunk.ReasoningContent)
	}
	if chunk.Usage.TotalTokens != 15 {
		t.Errorf("Chat 用量未正确获取，实际 %d", chunk.Usage.TotalTokens)
	}
	if chunk.Finish != StopEnd {
		t.Errorf("Chat 终止原因错误: %v", chunk.Finish)
	}
}

func TestChatStream_RetriesOnRateLimit(t *testing.T) {
	var count int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		current := atomic.AddInt32(&count, 1)
		if current == 1 {
			w.Header().Set("Retry-After", "1")
			http.Error(w, `{"error":{"message":"rate limited"}}`, http.StatusTooManyRequests)
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"ok\"},\"finish_reason\":\"stop\"}]}\n\n")
		_, _ = io.WriteString(w, "data: [DONE]\n\n")
	}))
	defer server.Close()

	client, err := New(Config{
		BaseURL:  server.URL,
		APIKey:   "key",
		Model:    "m",
		Attempts: 2,
	})
	if err != nil {
		t.Fatalf("New failed: %v", err)
	}

	chunk, err := client.Chat(context.Background(), Request{
		Messages: []Message{{Role: RoleUser, Content: "ping"}},
	})
	if err != nil {
		t.Fatalf("重试后应成功，但返回错误: %v", err)
	}
	if chunk.Delta != "ok" {
		t.Errorf("期望 ok，实际 %q", chunk.Delta)
	}
	if atomic.LoadInt32(&count) != 2 {
		t.Errorf("期望请求 2 次，实际 %d 次", atomic.LoadInt32(&count))
	}
}

func TestChatStream_NoRetryOnAuthFailure(t *testing.T) {
	var count int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&count, 1)
		http.Error(w, `{"error":{"message":"invalid api key"}}`, http.StatusUnauthorized)
	}))
	defer server.Close()

	client, err := New(Config{
		BaseURL:  server.URL,
		APIKey:   "bad-key",
		Model:    "m",
		Attempts: 3,
	})
	if err != nil {
		t.Fatalf("New failed: %v", err)
	}

	_, err = client.Chat(context.Background(), Request{
		Messages: []Message{{Role: RoleUser, Content: "ping"}},
	})
	if err == nil {
		t.Fatalf("鉴权失败应报错")
	}
	if atomic.LoadInt32(&count) != 1 {
		t.Errorf("鉴权错误不应重试，实际请求 %d 次", atomic.LoadInt32(&count))
	}
}

func TestAPIError_RetryableRules(t *testing.T) {
	// 证书类错误不可重试
	certErr := &APIError{Err: &tls.CertificateVerificationError{}}
	if certErr.Retryable() {
		t.Errorf("证书错误不应重试")
	}

	// DNS Not Found 不可重试
	dnsErr := &APIError{Err: &net.DNSError{IsNotFound: true}}
	if dnsErr.Retryable() {
		t.Errorf("DNS 未找到不应重试")
	}

	// Context 取消不重试
	cancelErr := &APIError{Err: context.Canceled}
	if cancelErr.Retryable() {
		t.Errorf("Context Canceled 不应重试")
	}

	// 500、429 可重试
	serverErr := &APIError{Status: 502}
	if !serverErr.Retryable() {
		t.Errorf("502 应当可重试")
	}
	rateLimitErr := &APIError{Status: 429}
	if !rateLimitErr.Retryable() {
		t.Errorf("429 应当可重试")
	}
}
