package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"my-agent/internal/config"
)

// 测试 llama-server 健康检查与模型就绪检测
func TestLlamaCppGateway_HealthCheck(t *testing.T) {
	// 场景 1: 模型已就绪 (200 OK)
	serverOK := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"status":"ok"}`))
			return
		}
		http.NotFound(w, r)
	}))
	defer serverOK.Close()

	gwOK, _ := NewLlamaCppGateway(serverOK.URL, "", "local-model", serverOK.Client())
	if err := gwOK.CheckHealth(context.Background()); err != nil {
		t.Errorf("expected health check to pass, got: %v", err)
	}

	// 场景 2: 模型正在加载中 (503 Service Unavailable)
	serverLoading := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			w.WriteHeader(http.StatusServiceUnavailable)
			_, _ = w.Write([]byte(`{"status":"loading model"}`))
			return
		}
		http.NotFound(w, r)
	}))
	defer serverLoading.Close()

	gwLoading, _ := NewLlamaCppGateway(serverLoading.URL, "", "local-model", serverLoading.Client())
	err := gwLoading.CheckHealth(context.Background())
	if err == nil || !strings.Contains(err.Error(), "loading model") {
		t.Errorf("expected loading model error, got: %v", err)
	}
}

// 测试 llama.cpp 同步对话与 Token 统计
func TestLlamaCppGateway_Chat_Text(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/chat/completions" {
			http.NotFound(w, r)
			return
		}

		respJSON := `{
			"choices": [
				{
					"index": 0,
					"message": {
						"role": "assistant",
						"content": "Hello, I am running on local llama.cpp!"
					},
					"finish_reason": "stop"
				}
			],
			"usage": {
				"prompt_tokens": 8,
				"completion_tokens": 12,
				"total_tokens": 20
			}
		}`
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(respJSON))
	}))
	defer mockServer.Close()

	gw, err := NewLlamaCppGateway(mockServer.URL, "", "local-model", mockServer.Client())
	if err != nil {
		t.Fatalf("failed to create gateway: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	resp, err := gw.Chat(ctx, &ChatRequest{
		Messages: []Message{
			{Role: RoleSystem, Content: "You are a helpful coding assistant."},
			{Role: RoleUser, Content: "Hello!"},
		},
	})
	if err != nil {
		t.Fatalf("Chat failed: %v", err)
	}

	if resp.Content != "Hello, I am running on local llama.cpp!" {
		t.Errorf("unexpected content: %q", resp.Content)
	}
	if resp.Usage.TotalTokens != 20 {
		t.Errorf("expected 20 tokens, got %d", resp.Usage.TotalTokens)
	}
	if gw.GetTotalUsage().TotalTokens != 20 {
		t.Errorf("expected cumulative 20 tokens, got %d", gw.GetTotalUsage().TotalTokens)
	}
}

// 测试带有工具声明并返回 ToolCalls
func TestLlamaCppGateway_Chat_WithToolCalls(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var reqDTO llamaCppChatRequestDTO
		if err := json.NewDecoder(r.Body).Decode(&reqDTO); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		if len(reqDTO.Tools) != 1 || reqDTO.Tools[0].Function.Name != "read_file" {
			http.Error(w, "missing expected tool", http.StatusBadRequest)
			return
		}

		respJSON := `{
			"choices": [
				{
					"index": 0,
					"message": {
						"role": "assistant",
						"content": null,
						"tool_calls": [
							{
								"id": "call_12345",
								"type": "function",
								"function": {
									"name": "read_file",
									"arguments": "{\"path\":\"main.go\"}"
								}
							}
						]
					},
					"finish_reason": "tool_calls"
				}
			],
			"usage": {
				"prompt_tokens": 20,
				"completion_tokens": 10,
				"total_tokens": 30
			}
		}`
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(respJSON))
	}))
	defer mockServer.Close()

	gw, _ := NewLlamaCppGateway(mockServer.URL, "", "local-model", mockServer.Client())

	resp, err := gw.Chat(context.Background(), &ChatRequest{
		Messages: []Message{
			{Role: RoleUser, Content: "Read main.go"},
		},
		Tools: []ToolDefinition{
			{
				Name:        "read_file",
				Description: "Read file contents",
				Parameters:  json.RawMessage(`{"type":"object","properties":{"path":{"type":"string"}}}`),
			},
		},
	})
	if err != nil {
		t.Fatalf("Chat with tools failed: %v", err)
	}

	if len(resp.ToolCalls) != 1 {
		t.Fatalf("expected 1 tool call, got %d", len(resp.ToolCalls))
	}

	tc := resp.ToolCalls[0]
	if tc.ID != "call_12345" || tc.Name != "read_file" {
		t.Errorf("unexpected tool call: %+v", tc)
	}
	if string(tc.Arguments) != `{"path":"main.go"}` {
		t.Errorf("unexpected arguments: %s", string(tc.Arguments))
	}
}

// 测试回传 RoleTool (ToolResult) 给 llama.cpp
func TestLlamaCppGateway_Chat_WithToolResult(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var reqDTO llamaCppChatRequestDTO
		if err := json.NewDecoder(r.Body).Decode(&reqDTO); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		if len(reqDTO.Messages) != 3 {
			http.Error(w, fmt.Sprintf("expected 3 messages, got %d", len(reqDTO.Messages)), http.StatusBadRequest)
			return
		}

		toolMsg := reqDTO.Messages[2]
		if toolMsg.Role != "tool" || toolMsg.ToolCallID != "call_12345" || *toolMsg.Content != "package main" {
			http.Error(w, fmt.Sprintf("unexpected tool message: %+v", toolMsg), http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"choices": [{"message": {"role": "assistant", "content": "File read successfully."}}],
			"usage": {"total_tokens": 35}
		}`))
	}))
	defer mockServer.Close()

	gw, _ := NewLlamaCppGateway(mockServer.URL, "", "local-model", mockServer.Client())

	resp, err := gw.Chat(context.Background(), &ChatRequest{
		Messages: []Message{
			{Role: RoleUser, Content: "Read main.go"},
			{
				Role: RoleAssistant,
				ToolCalls: []ToolCall{
					{ID: "call_12345", Name: "read_file", Arguments: json.RawMessage(`{"path":"main.go"}`)},
				},
			},
			{
				Role: RoleTool,
				ToolResult: &ToolResult{
					ToolCallID: "call_12345",
					Name:       "read_file",
					Content:    "package main",
				},
			},
		},
	})
	if err != nil {
		t.Fatalf("Chat with tool result failed: %v", err)
	}

	if resp.Content != "File read successfully." {
		t.Errorf("unexpected content: %q", resp.Content)
	}
}

// 测试 llama.cpp 流式打字输出
func TestLlamaCppGateway_ChatStream_Text(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)

		flusher, ok := w.(http.Flusher)
		if !ok {
			return
		}

		lines := []string{
			`data: {"choices":[{"delta":{"content":"Llama "}}]}`,
			`data: {"choices":[{"delta":{"content":"streaming!"}}]}`,
			`data: {"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}`,
			`data: [DONE]`,
		}

		for _, line := range lines {
			_, _ = fmt.Fprintf(w, "%s\n\n", line)
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	gw, _ := NewLlamaCppGateway(mockServer.URL, "", "local-model", mockServer.Client())

	stream, err := gw.ChatStream(context.Background(), &ChatRequest{
		Messages: []Message{{Role: RoleUser, Content: "Hi"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var textBuilder strings.Builder
	var done bool
	var usage *Usage

	for chunk := range stream {
		if chunk.Err != nil {
			t.Fatalf("unexpected chunk error: %v", chunk.Err)
		}
		if chunk.Delta != "" {
			textBuilder.WriteString(chunk.Delta)
		}
		if chunk.Done {
			done = true
			usage = chunk.Usage
		}
	}

	if !done {
		t.Errorf("expected stream to finish with Done=true")
	}
	if textBuilder.String() != "Llama streaming!" {
		t.Errorf("expected 'Llama streaming!', got %q", textBuilder.String())
	}
	if usage == nil || usage.TotalTokens != 7 {
		t.Errorf("unexpected usage: %+v", usage)
	}
}

// 测试流式 tool_calls 碎片聚合
func TestLlamaCppGateway_ChatStream_ToolCallsAggregation(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)

		flusher, ok := w.(http.Flusher)
		if !ok {
			return
		}

		lines := []string{
			`data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_999","type":"function","function":{"name":"run_bash","arguments":"{\"cmd"}}]}}]}`,
			`data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\":\"ls -la"}}]}}]}`,
			`data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\"}"}}]}}]}`,
			`data: {"usage":{"prompt_tokens":10,"completion_tokens":15,"total_tokens":25}}`,
			`data: [DONE]`,
		}

		for _, line := range lines {
			_, _ = fmt.Fprintf(w, "%s\n\n", line)
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	gw, _ := NewLlamaCppGateway(mockServer.URL, "", "local-model", mockServer.Client())

	stream, err := gw.ChatStream(context.Background(), &ChatRequest{
		Messages: []Message{{Role: RoleUser, Content: "Run ls"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var finalCalls []ToolCall
	var done bool

	for chunk := range stream {
		if chunk.Err != nil {
			t.Fatalf("unexpected chunk error: %v", chunk.Err)
		}
		if chunk.Done {
			done = true
			finalCalls = chunk.ToolCalls
		}
	}

	if !done {
		t.Fatalf("expected stream to finish with Done=true")
	}

	if len(finalCalls) != 1 {
		t.Fatalf("expected 1 aggregated tool call, got %d", len(finalCalls))
	}

	tc := finalCalls[0]
	if tc.ID != "call_999" || tc.Name != "run_bash" {
		t.Errorf("unexpected tool call: %+v", tc)
	}
	if string(tc.Arguments) != `{"cmd":"ls -la"}` {
		t.Errorf("expected '{\"cmd\":\"ls -la\"}', got %q", string(tc.Arguments))
	}
}

// 测试异常场景（空消息等）
func TestLlamaCppGateway_Errors(t *testing.T) {
	gw, _ := NewLlamaCppGateway("http://127.0.0.1:8080", "", "local-model", nil)

	_, err := gw.Chat(context.Background(), nil)
	if err != ErrEmptyMessages {
		t.Errorf("expected ErrEmptyMessages, got %v", err)
	}

	_, err = gw.ChatStream(context.Background(), nil)
	if err != ErrEmptyMessages {
		t.Errorf("expected ErrEmptyMessages, got %v", err)
	}
}

// 测试工厂方法 NewGatewayFromConfig
func TestNewGatewayFromConfig(t *testing.T) {
	cfg := &config.Config{
		Provider: config.ProviderLlamaCpp,
		BaseURL:  "http://localhost:8080",
	}

	gw, err := NewGatewayFromConfig(cfg)
	if err != nil {
		t.Fatalf("failed to create gateway from config: %v", err)
	}

	lgw, ok := gw.(*LlamaCppGateway)
	if !ok {
		t.Fatalf("expected *LlamaCppGateway, got %T", gw)
	}

	if lgw.baseURL != "http://localhost:8080" {
		t.Errorf("expected baseURL http://localhost:8080, got %s", lgw.baseURL)
	}
	if lgw.model != config.DefaultLlamaCppModel {
		t.Errorf("expected default model %s, got %s", config.DefaultLlamaCppModel, lgw.model)
	}

	// 测试 DeepSeek 官方配置
	dsCfg := &config.Config{
		Provider: config.ProviderDeepSeek,
		APIKey:   "sk-deepseek-test",
	}
	dsGw, err := NewGatewayFromConfig(dsCfg)
	if err != nil {
		t.Fatalf("failed to create deepseek gateway: %v", err)
	}
	dsLgw, ok := dsGw.(*LlamaCppGateway)
	if !ok {
		t.Fatalf("expected *LlamaCppGateway, got %T", dsGw)
	}
	if dsLgw.baseURL != config.DeepSeekBaseURL {
		t.Errorf("expected deepseek baseURL %s, got %s", config.DeepSeekBaseURL, dsLgw.baseURL)
	}
	if dsLgw.model != config.DefaultDeepSeekModel {
		t.Errorf("expected deepseek model %s, got %s", config.DefaultDeepSeekModel, dsLgw.model)
	}

	// 测试 Google Gemini 官方配置 (要求有效 APIKey)
	geminiCfg := &config.Config{
		Provider: config.ProviderGemini,
		APIKey:   "sk-gemini-test-key",
	}
	geminiGw, err := NewGatewayFromConfig(geminiCfg)
	if err != nil {
		t.Fatalf("failed to create gemini gateway: %v", err)
	}
	geminiLgw, ok := geminiGw.(*LlamaCppGateway)
	if !ok {
		t.Fatalf("expected *LlamaCppGateway, got %T", geminiGw)
	}
	if geminiLgw.baseURL != config.GeminiBaseURL {
		t.Errorf("expected gemini baseURL %s, got %s", config.GeminiBaseURL, geminiLgw.baseURL)
	}
	if geminiLgw.model != config.DefaultGeminiModel {
		t.Errorf("expected gemini model %s, got %s", config.DefaultGeminiModel, geminiLgw.model)
	}

	// 测试 Gemini 缺少 APIKey 返回 ErrEmptyAPIKey
	geminiNoKeyCfg := &config.Config{
		Provider: config.ProviderGemini,
		APIKey:   "",
	}
	if _, err := NewGatewayFromConfig(geminiNoKeyCfg); err != ErrEmptyAPIKey {
		t.Errorf("expected ErrEmptyAPIKey for gemini without api key, got: %v", err)
	}

	// 测试 nil 配置与不支持的提供商
	if _, err := NewGatewayFromConfig(nil); err == nil {
		t.Errorf("expected error for nil config")
	}
	if _, err := NewGatewayFromConfig(&config.Config{Provider: "unsupported_provider"}); err == nil {
		t.Errorf("expected error for unsupported provider")
	}
}
