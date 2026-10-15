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

// Gemini 通过 Google 官方 OpenAI 兼容端点调用 Gemini 模型
type Gemini struct {
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client

	mu         sync.RWMutex
	totalUsage Usage
}

// NewGemini 创建 Gemini 网关实例
func NewGemini(baseURL, apiKey, model string, client *http.Client) (*Gemini, error) {
	baseURL = strings.TrimSpace(baseURL)
	if baseURL == "" {
		baseURL = config.GeminiBaseURL
	}
	apiKey = strings.TrimSpace(apiKey)
	if apiKey == "" {
		return nil, ErrEmptyAPIKey
	}
	if strings.TrimSpace(model) == "" {
		model = config.DefaultGeminiModel
	}
	if client == nil {
		client = http.DefaultClient
	}
	return &Gemini{
		baseURL:    strings.TrimRight(baseURL, "/"),
		apiKey:     apiKey,
		model:      strings.TrimSpace(model),
		httpClient: client,
	}, nil
}

func (g *Gemini) endpoint() string {
	return chatURL(g.baseURL)
}

func (g *Gemini) setAuth(req *http.Request) {
	req.Header.Set("Authorization", "Bearer "+g.apiKey)
	req.Header.Set("x-goog-api-key", g.apiKey)
}

// Chat 执行同步对话调用
func (g *Gemini) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	httpReq, err := buildHTTPRequest(ctx, g.endpoint(), g.model, req, false)
	if err != nil {
		return nil, err
	}
	g.setAuth(httpReq)

	resp, err := g.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("gemini: http error: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("gemini: read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("gemini: status %d: %s", resp.StatusCode, string(body))
	}

	content, toolCalls, usage, err := parseResponse(body)
	if err != nil {
		return nil, fmt.Errorf("gemini: %w", err)
	}

	g.mu.Lock()
	g.totalUsage.Add(usage)
	g.mu.Unlock()

	return &ChatResponse{Content: content, ToolCalls: toolCalls, Usage: usage}, nil
}

// ChatStream 执行流式调用
func (g *Gemini) ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error) {
	httpReq, err := buildHTTPRequest(ctx, g.endpoint(), g.model, req, true)
	if err != nil {
		return nil, err
	}
	g.setAuth(httpReq)

	resp, err := g.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("gemini: http stream error: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		return nil, fmt.Errorf("gemini: stream status %d: %s", resp.StatusCode, string(body))
	}

	out := make(chan StreamChunk, 32)
	go func() {
		defer resp.Body.Close()
		defer close(out)
		usage := readSSE(ctx, resp.Body, out)
		if usage.TotalTokens > 0 {
			g.mu.Lock()
			g.totalUsage.Add(usage)
			g.mu.Unlock()
		}
	}()

	return out, nil
}

// TotalUsage 获取累计 Token 用量
func (g *Gemini) TotalUsage() Usage {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.totalUsage
}
