package gateway

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"

	"my-agent/internal/config"
)

// LlamaCpp 通过 llama-server 的 HTTP 服务调用本地模型
type LlamaCpp struct {
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client

	mu         sync.RWMutex
	totalUsage Usage
}

// NewLlamaCpp 创建 llama.cpp 本地网关实例
func NewLlamaCpp(baseURL, apiKey, model string, client *http.Client) (*LlamaCpp, error) {
	baseURL = strings.TrimSpace(baseURL)
	if baseURL == "" {
		baseURL = config.DefaultLlamaCppBaseURL
	}
	if strings.TrimSpace(model) == "" {
		model = config.DefaultLlamaCppModel
	}
	if client == nil {
		client = http.DefaultClient
	}
	return &LlamaCpp{
		baseURL:    strings.TrimRight(baseURL, "/"),
		apiKey:     strings.TrimSpace(apiKey),
		model:      strings.TrimSpace(model),
		httpClient: client,
	}, nil
}

// CheckHealth 检查 llama-server 服务健康与模型加载状态
func (l *LlamaCpp) CheckHealth(ctx context.Context) error {
	url := l.baseURL + "/health"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return fmt.Errorf("llamacpp: create health request: %w", err)
	}

	resp, err := l.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("llamacpp: server unreachable at %s: %w", l.baseURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		return nil
	}
	if resp.StatusCode == http.StatusServiceUnavailable {
		return fmt.Errorf("llamacpp: server is still loading model (503 Service Unavailable)")
	}

	body, _ := io.ReadAll(resp.Body)
	return fmt.Errorf("llamacpp: health check status %d: %s", resp.StatusCode, string(body))
}

func (l *LlamaCpp) endpoint() string {
	return chatURL(l.baseURL)
}

func (l *LlamaCpp) setAuth(req *http.Request) {
	if l.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+l.apiKey)
	}
}

// Chat 执行同步对话调用
func (l *LlamaCpp) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	httpReq, err := buildHTTPRequest(ctx, l.endpoint(), l.model, req, false)
	if err != nil {
		return nil, err
	}
	l.setAuth(httpReq)

	resp, err := l.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("llamacpp: http error: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("llamacpp: read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("llamacpp: status %d: %s", resp.StatusCode, string(body))
	}

	content, toolCalls, usage, err := parseResponse(body)
	if err != nil {
		return nil, fmt.Errorf("llamacpp: %w", err)
	}

	l.mu.Lock()
	l.totalUsage.Add(usage)
	l.mu.Unlock()

	return &ChatResponse{Content: content, ToolCalls: toolCalls, Usage: usage}, nil
}

// ChatStream 执行流式调用
func (l *LlamaCpp) ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error) {
	httpReq, err := buildHTTPRequest(ctx, l.endpoint(), l.model, req, true)
	if err != nil {
		return nil, err
	}
	l.setAuth(httpReq)

	resp, err := l.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("llamacpp: http stream error: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		return nil, fmt.Errorf("llamacpp: stream status %d: %s", resp.StatusCode, string(body))
	}

	out := make(chan StreamChunk, 32)
	go func() {
		defer resp.Body.Close()
		defer close(out)
		usage := readSSE(ctx, resp.Body, out)
		if usage.TotalTokens > 0 {
			l.mu.Lock()
			l.totalUsage.Add(usage)
			l.mu.Unlock()
		}
	}()

	return out, nil
}

// TotalUsage 获取累计 Token 用量
func (l *LlamaCpp) TotalUsage() Usage {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.totalUsage
}
