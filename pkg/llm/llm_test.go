package llm

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

// newTestClient 构造指向测试服务器的客户端（默认不重试）。
func newTestClient(t *testing.T, url string) *Client {
	t.Helper()
	return newTestClientWith(t, Config{
		Provider: ProviderDeepSeek,
		BaseURL:  url,
		APIKey:   "test-key",
		Attempts: 1,
	})
}

func newTestClientWith(t *testing.T, cfg Config) *Client {
	t.Helper()
	c, err := New(cfg)
	if err != nil {
		t.Fatalf("构造客户端失败: %v", err)
	}
	return c
}

// collect 读取整条流，返回增量序列与终块。
func collect(t *testing.T, stream <-chan Chunk) ([]string, Chunk) {
	t.Helper()

	var deltas []string
	var terminal Chunk
	for chunk := range stream {
		if chunk.Terminal() {
			terminal = chunk
			continue
		}
		if chunk.Delta != "" {
			deltas = append(deltas, chunk.Delta)
		}
	}
	return deltas, terminal
}

// 未知厂商与空厂商必须显式失败；库内不做任何别名解析
func TestNew_UnknownProvider(t *testing.T) {
	for _, p := range []Provider{"", "custom", "openai", "ds", "不存在的厂商"} {
		if _, err := New(Config{Provider: p, APIKey: "k"}); !errors.Is(err, ErrUnknownProvider) {
			t.Errorf("provider %q 应返回 ErrUnknownProvider，实际 %v", p, err)
		}
	}
}

// 远程厂商缺密钥返回 ErrNoAPIKey；本地厂商免密钥
func TestNew_KeyRules(t *testing.T) {
	if _, err := New(Config{Provider: ProviderDeepSeek}); !errors.Is(err, ErrNoAPIKey) {
		t.Errorf("远程厂商缺密钥应返回 ErrNoAPIKey，实际 %v", err)
	}
	if _, err := New(Config{Provider: ProviderLlamaCpp}); err != nil {
		t.Errorf("本地厂商不应要求密钥，实际 %v", err)
	}
}

// 默认值补齐与 Config 覆盖
func TestNew_DefaultsAndOverrides(t *testing.T) {
	c, err := New(Config{Provider: ProviderGemini, APIKey: "  g-key  "})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.Provider() != ProviderGemini {
		t.Errorf("厂商标识错误: %s", c.Provider())
	}
	if c.Model() != "gemini-2.5-flash" {
		t.Errorf("默认模型错误: %s", c.Model())
	}
	if c.BaseURL() != "https://generativelanguage.googleapis.com/v1beta/openai" {
		t.Errorf("默认根地址不正确: %s", c.BaseURL())
	}
	if c.apiKey != "g-key" {
		t.Errorf("密钥应被裁剪，实际 %q", c.apiKey)
	}
	if c.attempts != defaultAttempts {
		t.Errorf("默认尝试次数应为 %d，实际 %d", defaultAttempts, c.attempts)
	}
	if c.timeout != defaultStreamTimeout {
		t.Errorf("默认超时应为 %v，实际 %v", defaultStreamTimeout, c.timeout)
	}

	custom, err := New(Config{
		Provider:   ProviderDeepSeek,
		APIKey:     "k",
		BaseURL:    "  https://example.com/  ",
		Model:      "  deepseek-reasoner  ",
		Attempts:   1,
		Timeout:    time.Minute,
		HTTPClient: &http.Client{},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if custom.BaseURL() != "https://example.com" {
		t.Errorf("根地址应去除尾部斜杠，实际 %q", custom.BaseURL())
	}
	if custom.Model() != "deepseek-reasoner" {
		t.Errorf("模型应被裁剪，实际 %q", custom.Model())
	}
	if custom.attempts != 1 || custom.timeout != time.Minute {
		t.Errorf("覆盖未生效: attempts=%d timeout=%v", custom.attempts, custom.timeout)
	}
	if custom.httpClient == nil {
		t.Errorf("应保留注入的 HTTPClient")
	}
}

// 空消息在发请求前就被拒绝，不浪费一次网络往返
func TestChatStream_EmptyMessages(t *testing.T) {
	c := newTestClient(t, "http://127.0.0.1:1")
	if _, err := c.ChatStream(t.Context(), Request{}); !errors.Is(err, ErrEmptyMessages) {
		t.Errorf("期望 ErrEmptyMessages，实际 %v", err)
	}
}

// 用户自主提供 BaseURL, APIKey, Model，无需指定 Provider 即可工作
func TestNew_CustomBaseURLAndKey(t *testing.T) {
	c, err := New(Config{
		BaseURL: "https://my-proxy.internal/v1",
		APIKey:  "sk-custom-123456",
		Model:   "gpt-4o",
	})
	if err != nil {
		t.Fatalf("仅提供 BaseURL, APIKey, Model 应当成功: %v", err)
	}
	if c.Provider() != ProviderOpenAI {
		t.Errorf("期望默认 Provider 为 openai, 实际: %s", c.Provider())
	}
	if c.Model() != "gpt-4o" {
		t.Errorf("期望模型为 gpt-4o, 实际: %s", c.Model())
	}
	if c.BaseURL() != "https://my-proxy.internal/v1" {
		t.Errorf("期望 BaseURL 一致, 实际: %s", c.BaseURL())
	}
}

// 本地自建服务（127.0.0.1 / localhost）免 APIKey
func TestNew_CustomLocalBaseURLNoKey(t *testing.T) {
	c, err := New(Config{
		BaseURL: "http://127.0.0.1:11434/v1",
		Model:   "llama3",
	})
	if err != nil {
		t.Fatalf("本地服务应允许免 key: %v", err)
	}
	if c.Model() != "llama3" {
		t.Errorf("期望模型为 llama3, 实际: %s", c.Model())
	}
}

// Chat 同步调用自动累加流式增量与用量并返回完整终块
func TestClient_Chat_Unary(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"Hello, \"}}]}\n\n")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"World!\"},\"finish_reason\":\"stop\"}],\"usage\":{\"total_tokens\":10}}\n\n")
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
	if chunk.Usage.TotalTokens != 10 {
		t.Errorf("Chat 用量未正确获取，实际 %d", chunk.Usage.TotalTokens)
	}
	if chunk.Finish != StopEnd {
		t.Errorf("Chat 终止原因错误: %v", chunk.Finish)
	}
}
