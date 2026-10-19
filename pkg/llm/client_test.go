package llm

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestNew_Validations(t *testing.T) {
	// 远程厂商缺少 API Key 报错
	_, err := New(ProviderDeepSeek)
	if err != ErrEmptyAPIKey {
		t.Fatalf("expected ErrEmptyAPIKey, got: %v", err)
	}

	// 本地厂商无需 API Key
	client, err := New(ProviderLlamaCpp)
	if err != nil {
		t.Fatalf("expected success for local provider, got: %v", err)
	}
	if client.BaseURL() != DefaultLlamaCppBaseURL {
		t.Errorf("expected default baseURL %s, got %s", DefaultLlamaCppBaseURL, client.BaseURL())
	}
	if client.Model() != DefaultLlamaCppModel {
		t.Errorf("expected default model %s, got %s", DefaultLlamaCppModel, client.Model())
	}

	// 自定义选项生效
	customClient, err := New(
		ProviderCustom,
		WithAPIKey("test-key"),
		WithBaseURL("https://my-proxy.com/v1"),
		WithModel("my-custom-model"),
		WithHeader("X-Custom-Org", "my-org"),
	)
	if err != nil {
		t.Fatalf("create custom client failed: %v", err)
	}
	if customClient.BaseURL() != "https://my-proxy.com/v1" {
		t.Errorf("expected custom baseURL, got %s", customClient.BaseURL())
	}
	if customClient.Model() != "my-custom-model" {
		t.Errorf("expected custom model, got %s", customClient.Model())
	}
}

func TestChatStream_Basic(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/chat/completions" {
			http.NotFound(w, r)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)

		chunks := []string{
			`data: {"choices":[{"delta":{"content":"Hello"}}]}`,
			`data: {"choices":[{"delta":{"content":" World!"}}]}`,
			`data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}`,
			`data: [DONE]`,
		}
		for _, c := range chunks {
			_, _ = fmt.Fprintf(w, "%s\n\n", c)
			flusher.Flush()
		}
	}))
	defer server.Close()

	client, err := New(
		ProviderLlamaCpp,
		WithBaseURL(server.URL),
		WithHTTPClient(server.Client()),
	)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	stream, err := client.ChatStream(context.Background(), &ChatRequest{
		Messages: []Message{
			{Role: RoleUser, Content: "hi"},
		},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var text strings.Builder
	var lastUsage *Usage
	for chunk := range stream {
		if chunk.Err != nil {
			t.Fatalf("unexpected chunk error: %v", chunk.Err)
		}
		text.WriteString(chunk.Delta)
		if chunk.Usage != nil {
			lastUsage = chunk.Usage
		}
	}

	if text.String() != "Hello World!" {
		t.Errorf("expected 'Hello World!', got %q", text.String())
	}
	if lastUsage == nil || lastUsage.TotalTokens != 15 {
		t.Errorf("expected 15 total tokens, got %+v", lastUsage)
	}
	if client.TotalUsage().TotalTokens != 15 {
		t.Errorf("expected client cumulative 15 tokens, got %d", client.TotalUsage().TotalTokens)
	}
}

func TestChatStream_ReasoningAndToolCalls(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)

		chunks := []string{
			`data: {"choices":[{"delta":{"reasoning_content":"Thinking..."}}]}`,
			`data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"read_","arguments":"{\"path\":"}}]}}]}`,
			`data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"file","arguments":"\"test.txt\"}"}}]}}]}`,
			`data: [DONE]`,
		}
		for _, c := range chunks {
			_, _ = fmt.Fprintf(w, "%s\n\n", c)
			flusher.Flush()
		}
	}))
	defer server.Close()

	client, err := New(
		ProviderLlamaCpp,
		WithBaseURL(server.URL),
		WithHTTPClient(server.Client()),
	)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	stream, err := client.ChatStream(context.Background(), &ChatRequest{
		Messages: []Message{{Role: RoleUser, Content: "read file"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var reasoning strings.Builder
	var toolCalls []ToolCall
	for chunk := range stream {
		reasoning.WriteString(chunk.ReasoningContent)
		if len(chunk.ToolCalls) > 0 {
			toolCalls = append(toolCalls, chunk.ToolCalls...)
		}
	}

	if reasoning.String() != "Thinking..." {
		t.Errorf("expected 'Thinking...', got %q", reasoning.String())
	}
	if len(toolCalls) != 1 {
		t.Fatalf("expected 1 tool call, got %d", len(toolCalls))
	}
	if toolCalls[0].ID != "call_1" || toolCalls[0].Name != "read_file" || toolCalls[0].Arguments != `{"path":"test.txt"}` {
		t.Errorf("unexpected tool call: %+v", toolCalls[0])
	}
}

func TestChatStream_AuthHeaders(t *testing.T) {
	var capturedAuth, capturedGoogKey string

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedAuth = r.Header.Get("Authorization")
		capturedGoogKey = r.Header.Get("x-goog-api-key")

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = fmt.Fprintf(w, "data: [DONE]\n\n")
	}))
	defer server.Close()

	client, err := New(
		ProviderGemini,
		WithAPIKey("gemini-secret-token"),
		WithBaseURL(server.URL),
		WithHTTPClient(server.Client()),
	)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	stream, err := client.ChatStream(context.Background(), &ChatRequest{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}
	for range stream {
	}

	if capturedAuth != "Bearer gemini-secret-token" {
		t.Errorf("unexpected Authorization header: %s", capturedAuth)
	}
	if capturedGoogKey != "gemini-secret-token" {
		t.Errorf("unexpected x-goog-api-key header: %s", capturedGoogKey)
	}
}

func TestChatStream_RetryOn500(t *testing.T) {
	var attempts int

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attempts++
		if attempts < 3 {
			http.Error(w, "server error", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = fmt.Fprintf(w, "data: {\"choices\":[{\"delta\":{\"content\":\"Recovered!\"}}]}\n\ndata: [DONE]\n\n")
	}))
	defer server.Close()

	client, err := New(
		ProviderLlamaCpp,
		WithBaseURL(server.URL),
		WithHTTPClient(server.Client()),
		WithMaxRetries(3),
	)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	stream, err := client.ChatStream(context.Background(), &ChatRequest{
		Messages: []Message{{Role: RoleUser, Content: "retry me"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var text strings.Builder
	for chunk := range stream {
		text.WriteString(chunk.Delta)
	}

	if text.String() != "Recovered!" {
		t.Errorf("expected 'Recovered!', got %q", text.String())
	}
	if attempts != 3 {
		t.Errorf("expected 3 attempts, got %d", attempts)
	}
}

func TestChat_Synchronous(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)

		_, _ = fmt.Fprintf(w, "data: {\"choices\":[{\"delta\":{\"content\":\"Sync Hello\"}}]}\n\n")
		flusher.Flush()
		_, _ = fmt.Fprintf(w, "data: [DONE]\n\n")
		flusher.Flush()
	}))
	defer server.Close()

	client, err := New(
		ProviderLlamaCpp,
		WithBaseURL(server.URL),
		WithHTTPClient(server.Client()),
	)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	resp, err := client.Chat(context.Background(), &ChatRequest{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("Chat failed: %v", err)
	}

	if resp.Delta != "Sync Hello" {
		t.Errorf("expected 'Sync Hello', got %q", resp.Delta)
	}
}

// 验证输入包含 reasoning_content 时，请求体中被剥离不发送
func TestChatStream_ReasoningNotSentInRequestBody(t *testing.T) {
	var receivedBody string

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var raw map[string]any
		_ = json.NewDecoder(r.Body).Decode(&raw)
		data, _ := json.Marshal(raw)
		receivedBody = string(data)

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = fmt.Fprintf(w, "data: [DONE]\n\n")
	}))
	defer server.Close()

	client, err := New(
		ProviderLlamaCpp,
		WithBaseURL(server.URL),
		WithHTTPClient(server.Client()),
	)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	stream, err := client.ChatStream(context.Background(), &ChatRequest{
		Messages: []Message{
			{Role: RoleAssistant, Content: "Hello", ReasoningContent: "Secret Thought"},
		},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}
	for range stream {
	}

	if strings.Contains(receivedBody, "reasoning_content") || strings.Contains(receivedBody, "Secret Thought") {
		t.Errorf("request body MUST NOT contain reasoning_content, got: %s", receivedBody)
	}
}

func TestProbeLocalService(t *testing.T) {
	// 1. 服务就绪场景
	readyServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/models" {
			http.NotFound(w, r)
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"data":[]}`))
	}))
	defer readyServer.Close()

	if err := ProbeLocalService(context.Background(), readyServer.URL); err != nil {
		t.Fatalf("expected ProbeLocalService to succeed, got: %v", err)
	}

	// 2. 服务返回异常场景
	errServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "server busy", http.StatusServiceUnavailable)
	}))
	defer errServer.Close()

	if err := ProbeLocalService(context.Background(), errServer.URL); err == nil {
		t.Fatalf("expected error from unavailable service, got nil")
	}
}
