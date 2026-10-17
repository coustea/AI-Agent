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
	"my-agent/internal/protocol"
)

// streamResult 收集一次流式调用的完整结果。
type streamResult struct {
	content   string
	reasoning string
	toolCalls []protocol.ToolCall
	usage     *protocol.Usage
}

// collectStream 排空流式通道并聚合文本、思维链、工具调用与用量。
func collectStream(t *testing.T, stream <-chan protocol.ChatResponse) streamResult {
	t.Helper()
	var r streamResult
	for chunk := range stream {
		if chunk.Err != nil {
			t.Fatalf("stream chunk error: %v", chunk.Err)
		}
		r.content += chunk.Delta
		r.reasoning += chunk.ReasoningContent
		r.toolCalls = append(r.toolCalls, chunk.ToolCalls...)
		if chunk.Done && chunk.Usage != nil {
			r.usage = chunk.Usage
		}
	}
	return r
}

// 测试 llama-server 健康检查与模型就绪检测
func TestLlamaCpp_HealthCheck(t *testing.T) {
	serverOK := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"status":"ok"}`))
			return
		}
		http.NotFound(w, r)
	}))
	defer serverOK.Close()

	gwOK, _ := NewLlamaCpp(serverOK.URL, "", "local-model", serverOK.Client())
	if err := gwOK.CheckHealth(context.Background()); err != nil {
		t.Errorf("expected health check to pass, got: %v", err)
	}

	serverLoading := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			w.WriteHeader(http.StatusServiceUnavailable)
			_, _ = w.Write([]byte(`{"status":"loading model"}`))
			return
		}
		http.NotFound(w, r)
	}))
	defer serverLoading.Close()

	gwLoading, _ := NewLlamaCpp(serverLoading.URL, "", "local-model", serverLoading.Client())
	err := gwLoading.CheckHealth(context.Background())
	if err == nil || !strings.Contains(err.Error(), "loading model") {
		t.Errorf("expected loading model error, got: %v", err)
	}
}

// 测试 llama.cpp 流式对话与 Token 统计
func TestLlamaCpp_Chat_Text(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/chat/completions" {
			http.NotFound(w, r)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)
		for _, ev := range []string{
			`data: {"choices":[{"delta":{"content":"Hello, I am running on local llama.cpp!"}}]}`,
			`data: {"choices":[],"usage":{"prompt_tokens":8,"completion_tokens":12,"total_tokens":20}}`,
			`data: [DONE]`,
		} {
			_, _ = fmt.Fprintf(w, "%s\n\n", ev)
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	gw, err := NewLlamaCpp(mockServer.URL, "", "local-model", mockServer.Client())
	if err != nil {
		t.Fatalf("failed to create gateway: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	stream, err := gw.ChatStream(ctx, &protocol.ChatRequest{
		Messages: []protocol.Message{
			{Role: protocol.RoleSystem, Content: "You are a helpful assistant."},
			{Role: protocol.RoleUser, Content: "Hello!"},
		},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	res := collectStream(t, stream)
	if res.content != "Hello, I am running on local llama.cpp!" {
		t.Errorf("unexpected content: %s", res.content)
	}
	if res.usage == nil || res.usage.TotalTokens != 20 {
		t.Errorf("expected 20 tokens, got %+v", res.usage)
	}
	if gw.TotalUsage().TotalTokens != 20 {
		t.Errorf("expected cumulative 20 tokens, got %d", gw.TotalUsage().TotalTokens)
	}
}

// 测试带有工具声明并返回 ToolCalls
func TestLlamaCpp_Chat_WithToolCalls(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var wire wireReq
		if err := json.NewDecoder(r.Body).Decode(&wire); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		if len(wire.Tools) != 1 || wire.Tools[0].Function.Name != "read_file" {
			http.Error(w, "missing expected tool", http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)
		for _, ev := range []string{
			`data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_12345","type":"function","function":{"name":"read_file","arguments":"{\"path\":\"main.go\"}"}}]}}]}`,
			`data: [DONE]`,
		} {
			_, _ = fmt.Fprintf(w, "%s\n\n", ev)
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	gw, _ := NewLlamaCpp(mockServer.URL, "", "local-model", mockServer.Client())

	stream, err := gw.ChatStream(context.Background(), &protocol.ChatRequest{
		Messages: []protocol.Message{
			{Role: protocol.RoleUser, Content: "Read main.go"},
		},
		Tools: []protocol.ToolDefinition{
			{
				Name:        "read_file",
				Description: "Read file contents",
				Parameters:  json.RawMessage(`{"type":"object","properties":{"path":{"type":"string"}}}`),
			},
		},
	})
	if err != nil {
		t.Fatalf("ChatStream with tools failed: %v", err)
	}

	res := collectStream(t, stream)
	if len(res.toolCalls) != 1 {
		t.Fatalf("expected 1 tool call, got %d", len(res.toolCalls))
	}

	tc := res.toolCalls[0]
	if tc.ID != "call_12345" || tc.Name != "read_file" {
		t.Errorf("unexpected tool call: %+v", tc)
	}
	if string(tc.Arguments) != `{"path":"main.go"}` {
		t.Errorf("unexpected arguments: %s", string(tc.Arguments))
	}
}

// 测试回传 RoleTool (ToolResult)
func TestLlamaCpp_Chat_WithToolResult(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var wire wireReq
		if err := json.NewDecoder(r.Body).Decode(&wire); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		if len(wire.Messages) != 3 {
			http.Error(w, fmt.Sprintf("expected 3 messages, got %d", len(wire.Messages)), http.StatusBadRequest)
			return
		}

		toolMsg := wire.Messages[2]
		if toolMsg.Role != "tool" || toolMsg.ToolCallID != "call_12345" || *toolMsg.Content != "package main" {
			http.Error(w, fmt.Sprintf("unexpected tool message: %+v", toolMsg), http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)
		for _, ev := range []string{
			`data: {"choices":[{"delta":{"content":"File read successfully."}}]}`,
			`data: [DONE]`,
		} {
			_, _ = fmt.Fprintf(w, "%s\n\n", ev)
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	gw, _ := NewLlamaCpp(mockServer.URL, "", "local-model", mockServer.Client())

	stream, err := gw.ChatStream(context.Background(), &protocol.ChatRequest{
		Messages: []protocol.Message{
			{Role: protocol.RoleUser, Content: "Read main.go"},
			{
				Role: protocol.RoleAssistant,
				ToolCalls: []protocol.ToolCall{
					{ID: "call_12345", Name: "read_file", Arguments: `{"path":"main.go"}`},
				},
			},
			{
				Role: protocol.RoleTool,
				ToolResult: &protocol.ToolResult{
					ToolCallID: "call_12345",
					Name:       "read_file",
					Content:    "package main",
				},
			},
		},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	res := collectStream(t, stream)
	if res.content != "File read successfully." {
		t.Errorf("unexpected content: %s", res.content)
	}
}

// 测试流式文本输出与 Token 统计
func TestLlamaCpp_ChatStream_Text(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "streaming unsupported", http.StatusInternalServerError)
			return
		}

		events := []string{
			`data: {"choices":[{"delta":{"role":"assistant","content":"Hel"}}]}`,
			`data: {"choices":[{"delta":{"content":"lo"}}]}`,
			`data: {"choices":[{"delta":{"content":"!"}}]}`,
			`data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":3,"total_tokens":8}}`,
			`data: [DONE]`,
		}

		for _, ev := range events {
			_, _ = fmt.Fprintf(w, "%s\n\n", ev)
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	gw, _ := NewLlamaCpp(mockServer.URL, "", "local-model", mockServer.Client())

	stream, err := gw.ChatStream(context.Background(), &protocol.ChatRequest{
		Messages: []protocol.Message{{Role: protocol.RoleUser, Content: "Hi"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var sb strings.Builder
	var doneReceived bool
	var finalUsage *protocol.Usage

	for chunk := range stream {
		if chunk.Err != nil {
			t.Fatalf("unexpected chunk error: %v", chunk.Err)
		}
		if chunk.Delta != "" {
			sb.WriteString(chunk.Delta)
		}
		if chunk.Done {
			doneReceived = true
			finalUsage = chunk.Usage
		}
	}

	if !doneReceived {
		t.Errorf("expected done chunk")
	}
	if sb.String() != "Hello!" {
		t.Errorf("expected 'Hello!', got %q", sb.String())
	}
	if finalUsage == nil || finalUsage.TotalTokens != 8 {
		t.Errorf("expected 8 tokens, got %+v", finalUsage)
	}
}

// 测试独立实现的 DeepSeek 同步与流式调用 (含 reasoning_content)
func TestDeepSeek_Chat_Text_WithReasoning(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test-deepseek-key" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)

		events := []string{
			`data: {"choices":[{"delta":{"role":"assistant","reasoning_content":"Let me think."}}]}`,
			`data: {"choices":[{"delta":{"content":"Here is the answer."}}]}`,
			`data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":10,"total_tokens":20}}`,
			`data: [DONE]`,
		}

		for _, ev := range events {
			_, _ = fmt.Fprintf(w, "%s\n\n", ev)
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	ds, err := NewDeepSeek(mockServer.URL, "test-deepseek-key", "deepseek-flash", mockServer.Client())
	if err != nil {
		t.Fatalf("NewDeepSeek failed: %v", err)
	}

	stream, err := ds.ChatStream(context.Background(), &protocol.ChatRequest{
		Messages: []protocol.Message{{Role: protocol.RoleUser, Content: "Hello"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var reasoning, content string
	for chunk := range stream {
		if chunk.ReasoningContent != "" {
			reasoning += chunk.ReasoningContent
		}
		if chunk.Delta != "" {
			content += chunk.Delta
		}
	}

	if reasoning != "Let me think." {
		t.Errorf("expected 'Let me think.', got %q", reasoning)
	}
	if content != "Here is the answer." {
		t.Errorf("expected 'Here is the answer.', got %q", content)
	}
}

// 测试独立实现的 Google Gemini 兼容端点调用与双重 Key 认证
func TestGemini_Chat_Text_AndAuth(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 校验 Gemini 官方 OpenAI 端点 URL
		if !strings.HasSuffix(r.URL.Path, "/chat/completions") {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		// 校验 Authorization 和 x-goog-api-key
		if r.Header.Get("Authorization") != "Bearer test-gemini-key" || r.Header.Get("x-goog-api-key") != "test-gemini-key" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)
		for _, ev := range []string{
			`data: {"choices":[{"delta":{"content":"Hello from Gemini 2.5!"}}]}`,
			`data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":6,"total_tokens":11}}`,
			`data: [DONE]`,
		} {
			_, _ = fmt.Fprintf(w, "%s\n\n", ev)
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	gemini, err := NewGemini(mockServer.URL+"/v1beta/openai", "test-gemini-key", "gemini-2.5-flash", mockServer.Client())
	if err != nil {
		t.Fatalf("NewGemini failed: %v", err)
	}

	stream, err := gemini.ChatStream(context.Background(), &protocol.ChatRequest{
		Messages: []protocol.Message{{Role: protocol.RoleUser, Content: "Hello Gemini"}},
	})
	if err != nil {
		t.Fatalf("gemini.ChatStream failed: %v", err)
	}

	res := collectStream(t, stream)
	if res.content != "Hello from Gemini 2.5!" {
		t.Errorf("unexpected content: %s", res.content)
	}
	if res.usage == nil || res.usage.TotalTokens != 11 {
		t.Errorf("expected 11 tokens, got %+v", res.usage)
	}
}

// 测试整个系统通过先经过 Agent 然后经过 Gateway Router 进行模型分配与路由
func TestRouter_ModelAllocation(t *testing.T) {
	newSSEServer := func(content string) *httptest.Server {
		return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "text/event-stream")
			w.WriteHeader(http.StatusOK)
			flusher := w.(http.Flusher)
			for _, ev := range []string{
				fmt.Sprintf(`data: {"choices":[{"delta":{"content":%q}}]}`, content),
				`data: [DONE]`,
			} {
				_, _ = fmt.Fprintf(w, "%s\n\n", ev)
				flusher.Flush()
			}
		}))
	}

	geminiServer := newSSEServer("from-gemini")
	defer geminiServer.Close()
	dsServer := newSSEServer("from-deepseek")
	defer dsServer.Close()
	llamaServer := newSSEServer("from-llamacpp")
	defer llamaServer.Close()

	geminiGW, _ := NewGemini(geminiServer.URL, "key", "gemini-2.5-flash", geminiServer.Client())
	dsGW, _ := NewDeepSeek(dsServer.URL, "key", "deepseek-flash", dsServer.Client())
	llamaGW, _ := NewLlamaCpp(llamaServer.URL, "", "local-model", llamaServer.Client())

	router := NewRouter("llamacpp")
	router.Register("gemini", geminiGW)
	router.Register("deepseek", dsGW)
	router.Register("llamacpp", llamaGW)

	route := func(modelName, want string) {
		t.Helper()
		stream, err := router.ChatStream(context.Background(), &protocol.ChatRequest{
			Model:    modelName,
			Messages: []protocol.Message{{Role: protocol.RoleUser, Content: "Hi"}},
		})
		if err != nil {
			t.Fatalf("route(%q) failed: %v", modelName, err)
		}
		if got := collectStream(t, stream).content; got != want {
			t.Fatalf("route(%q): expected content %q, got %q", modelName, want, got)
		}
	}

	// 1. 请求指定 gemini 模型 -> 自动分配到 gemini
	route("gemini-2.5-flash", "from-gemini")

	// 2. 请求指定 deepseek 模型 -> 自动分配到 deepseek
	route("deepseek-flash", "from-deepseek")

	// 3. 请求未指定模型 -> 自动分配到默认激活的 llamacpp
	route("", "from-llamacpp")

	// 4. 切换默认激活为 deepseek
	router.SetActive("deepseek")
	route("", "from-deepseek")
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

	router, ok := gw.(*Router)
	if !ok {
		t.Fatalf("expected *Router, got %T", gw)
	}

	activeGW, err := router.Route(&protocol.ChatRequest{})
	if err != nil {
		t.Fatalf("failed to route active gateway: %v", err)
	}

	lgw, ok := activeGW.(*Client)
	if !ok || lgw.Provider() != config.ProviderLlamaCpp {
		t.Fatalf("expected *Client for llamacpp, got %T", activeGW)
	}
	if lgw.baseURL != "http://localhost:8080" {
		t.Errorf("expected baseURL http://localhost:8080, got %s", lgw.baseURL)
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
	dsRouter := dsGw.(*Router)
	dsSubGW, _ := dsRouter.Route(&protocol.ChatRequest{})
	if client, ok := dsSubGW.(*Client); !ok || client.Provider() != config.ProviderDeepSeek {
		t.Fatalf("expected *Client for deepseek, got %T", dsSubGW)
	}

	// 测试 Google Gemini 官方配置
	geminiCfg := &config.Config{
		Provider: config.ProviderGemini,
		APIKey:   "sk-gemini-test-key",
	}
	geminiGw, err := NewGatewayFromConfig(geminiCfg)
	if err != nil {
		t.Fatalf("failed to create gemini gateway: %v", err)
	}
	geminiRouter := geminiGw.(*Router)
	geminiSubGW, _ := geminiRouter.Route(&protocol.ChatRequest{})
	if client, ok := geminiSubGW.(*Client); !ok || client.Provider() != config.ProviderGemini {
		t.Fatalf("expected *Client for gemini, got %T", geminiSubGW)
	}

	// 测试 Spark (星辰 MaaS) 配置与动态路由
	sparkCfg := &config.Config{
		Provider: config.ProviderSpark,
		APIKey:   "sk-spark-test-key",
	}
	sparkGw, err := NewGatewayFromConfig(sparkCfg)
	if err != nil {
		t.Fatalf("failed to create spark gateway: %v", err)
	}
	sparkRouter := sparkGw.(*Router)
	sparkSubGW, _ := sparkRouter.Route(&protocol.ChatRequest{})
	if client, ok := sparkSubGW.(*Client); !ok || client.Provider() != config.ProviderSpark {
		t.Fatalf("expected *Client for spark, got %T", sparkSubGW)
	}

	// 测试根据 spark-* 模型前缀动态路由
	prefixGW, err := sparkRouter.Route(&protocol.ChatRequest{Model: "spark-x2.5"})
	if err != nil {
		t.Fatalf("failed to route spark-x2.5: %v", err)
	}
	if client, ok := prefixGW.(*Client); !ok || client.Provider() != config.ProviderSpark {
		t.Fatalf("expected *Client for spark-x2.5 model prefix, got %T", prefixGW)
	}

	// 测试 Spark 缺少 APIKey 返回 ErrEmptyAPIKey
	sparkNoKeyCfg := &config.Config{
		Provider: config.ProviderSpark,
		APIKey:   "",
	}
	if _, err := NewGatewayFromConfig(sparkNoKeyCfg); err != ErrEmptyAPIKey {
		t.Errorf("expected ErrEmptyAPIKey for spark without api key, got: %v", err)
	}

	// 测试 Gemini 缺少 APIKey 返回 ErrEmptyAPIKey
	geminiNoKeyCfg := &config.Config{
		Provider: config.ProviderGemini,
		APIKey:   "",
	}
	if _, err := NewGatewayFromConfig(geminiNoKeyCfg); err != ErrEmptyAPIKey {
		t.Errorf("expected ErrEmptyAPIKey for gemini without api key, got: %v", err)
	}
}

// 测试 apiClient 在遭遇 429 或 5xx 时自动指数退避重试并在第三次成功
func TestApiClient_RetryOn429And5xx(t *testing.T) {
	var attempts int
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attempts++
		if attempts == 1 {
			http.Error(w, `{"error":"rate limited"}`, http.StatusTooManyRequests)
			return
		}
		if attempts == 2 {
			http.Error(w, `{"error":"temporary gateway timeout"}`, http.StatusBadGateway)
			return
		}
		// 第三次成功返回 200
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)
		_, _ = fmt.Fprintf(w, "data: %s\n\n", `{"choices":[{"delta":{"content":"recovered"}}]}`)
		flusher.Flush()
		_, _ = fmt.Fprintf(w, "data: [DONE]\n\n")
		flusher.Flush()
	}))
	defer mockServer.Close()

	client, err := NewDeepSeek(mockServer.URL, "test-key", "deepseek-flash", mockServer.Client())
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	stream, err := client.ChatStream(context.Background(), &protocol.ChatRequest{
		Messages: []protocol.Message{{Role: protocol.RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("expected successful retry, got error: %v", err)
	}

	var content string
	for chunk := range stream {
		content += chunk.Delta
	}

	if attempts != 3 {
		t.Errorf("expected 3 attempts, got %d", attempts)
	}
	if content != "recovered" {
		t.Errorf("expected content 'recovered', got %q", content)
	}
}
