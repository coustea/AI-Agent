package gateway

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"my-agent/internal/config"
)

func TestSpark_NewSpark(t *testing.T) {
	// 1. 空 API Key 测试
	_, err := NewSpark("", "", "", nil)
	if err != ErrEmptyAPIKey {
		t.Fatalf("expected ErrEmptyAPIKey, got: %v", err)
	}

	// 2. 默认参数补齐测试
	gw, err := NewSpark("", "test-key", "", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if gw.baseURL != config.DefaultSparkBaseURL {
		t.Errorf("expected default baseURL %q, got %q", config.DefaultSparkBaseURL, gw.baseURL)
	}
	if gw.model != config.DefaultSparkModel {
		t.Errorf("expected default model %q, got %q", config.DefaultSparkModel, gw.model)
	}
	if gw.apiKey != "test-key" {
		t.Errorf("expected apiKey %q, got %q", "test-key", gw.apiKey)
	}
	if gw.httpClient == nil {
		t.Errorf("expected non-nil httpClient")
	}

	// 3. 自定义配置测试
	customClient := &http.Client{Timeout: 5 * time.Second}
	customGW, err := NewSpark("https://custom-spark.example.com/v2/", "custom-key", "spark-custom-model", customClient)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if customGW.baseURL != "https://custom-spark.example.com/v2" {
		t.Errorf("expected trimmed baseURL, got %q", customGW.baseURL)
	}
	if customGW.model != "spark-custom-model" {
		t.Errorf("expected spark-custom-model, got %q", customGW.model)
	}
	if customGW.httpClient != customClient {
		t.Errorf("expected customClient to be used")
	}
}

func TestSpark_Chat(t *testing.T) {
	const expectedKey = "spark-test-secret"
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v2/chat/completions" {
			t.Errorf("unexpected path: %s", r.URL.Path)
			http.NotFound(w, r)
			return
		}

		auth := r.Header.Get("Authorization")
		if auth != "Bearer "+expectedKey {
			t.Errorf("unexpected authorization header: %s", auth)
			w.WriteHeader(http.StatusUnauthorized)
			return
		}

		var reqBody map[string]any
		if err := json.NewDecoder(r.Body).Decode(&reqBody); err != nil {
			t.Errorf("failed to decode request body: %v", err)
			w.WriteHeader(http.StatusBadRequest)
			return
		}

		if reqBody["model"] != config.DefaultSparkModel {
			t.Errorf("expected model %q, got %v", config.DefaultSparkModel, reqBody["model"])
		}

		resp := `{
			"choices": [
				{
					"index": 0,
					"message": {
						"role": "assistant",
						"content": "Hello from Xingchen MaaS Spark!"
					},
					"finish_reason": "stop"
				}
			],
			"usage": {
				"prompt_tokens": 10,
				"completion_tokens": 15,
				"total_tokens": 25
			}
		}`
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(resp))
	}))
	defer mockServer.Close()

	// 传入 base 为 mockServer.URL + "/v2"
	gw, err := NewSpark(mockServer.URL+"/v2", expectedKey, "", mockServer.Client())
	if err != nil {
		t.Fatalf("failed to create spark gateway: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	resp, err := gw.Chat(ctx, &ChatRequest{
		Messages: []Message{
			{Role: RoleUser, Content: "Hello Spark!"},
		},
	})
	if err != nil {
		t.Fatalf("Chat failed: %v", err)
	}

	if resp.Content != "Hello from Xingchen MaaS Spark!" {
		t.Errorf("unexpected content: %q", resp.Content)
	}
	if resp.Usage.TotalTokens != 25 {
		t.Errorf("expected 25 total tokens, got %d", resp.Usage.TotalTokens)
	}

	usage := gw.TotalUsage()
	if usage.TotalTokens != 25 {
		t.Errorf("expected total usage 25, got %d", usage.TotalTokens)
	}
}

func TestSpark_ChatStream(t *testing.T) {
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v2/chat/completions" {
			http.NotFound(w, r)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)

		flusher, ok := w.(http.Flusher)
		if !ok {
			t.Fatalf("expected flusher")
		}

		chunks := []string{
			`data: {"choices":[{"delta":{"role":"assistant","content":"星辰"}}]}`,
			`data: {"choices":[{"delta":{"content":" MaaS"}}]}`,
			`data: {"choices":[{"delta":{"content":" 回复成功"}}],"usage":{"prompt_tokens":5,"completion_tokens":10,"total_tokens":15}}`,
			`data: [DONE]`,
		}

		for _, chunk := range chunks {
			_, _ = w.Write([]byte(chunk + "\n\n"))
			flusher.Flush()
		}
	}))
	defer mockServer.Close()

	gw, err := NewSpark(mockServer.URL+"/v2", "test-key", "", mockServer.Client())
	if err != nil {
		t.Fatalf("failed to create gateway: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	stream, err := gw.ChatStream(ctx, &ChatRequest{
		Messages: []Message{
			{Role: RoleUser, Content: "Hi"},
		},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var sb strings.Builder
	for chunk := range stream {
		if chunk.Err != nil {
			t.Fatalf("chunk error: %v", chunk.Err)
		}
		sb.WriteString(chunk.Delta)
	}

	expected := "星辰 MaaS 回复成功"
	if sb.String() != expected {
		t.Errorf("expected %q, got %q", expected, sb.String())
	}

	usage := gw.TotalUsage()
	if usage.TotalTokens != 15 {
		t.Errorf("expected 15 total tokens, got %d", usage.TotalTokens)
	}
}

func TestSpark_Errors(t *testing.T) {
	// 1. 空消息校验
	gw, _ := NewSpark("http://127.0.0.1:9999/v2", "key", "", nil)
	_, err := gw.Chat(context.Background(), &ChatRequest{Messages: nil})
	if err != ErrEmptyMessages {
		t.Errorf("expected ErrEmptyMessages, got: %v", err)
	}

	// 2. HTTP 错误状态码
	errServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusForbidden)
		_, _ = w.Write([]byte(`{"error":"insufficient quota"}`))
	}))
	defer errServer.Close()

	gwErr, _ := NewSpark(errServer.URL+"/v2", "key", "", errServer.Client())
	_, err = gwErr.Chat(context.Background(), &ChatRequest{
		Messages: []Message{{Role: RoleUser, Content: "Hello"}},
	})
	if err == nil || !strings.Contains(err.Error(), "403") {
		t.Errorf("expected 403 error, got: %v", err)
	}

	// 3. 流式 HTTP 错误状态码
	_, err = gwErr.ChatStream(context.Background(), &ChatRequest{
		Messages: []Message{{Role: RoleUser, Content: "Hello"}},
	})
	if err == nil || !strings.Contains(err.Error(), "403") {
		t.Errorf("expected 403 error for stream, got: %v", err)
	}
}
