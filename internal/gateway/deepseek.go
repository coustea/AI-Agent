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

// DeepSeek 通过 DeepSeek 官方 API 调用模型，支持深度思考链 (reasoning_content)
type DeepSeek struct {
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client

	mu         sync.RWMutex
	totalUsage Usage
}

// NewDeepSeek 创建 DeepSeek 网关实例
func NewDeepSeek(baseURL, apiKey, model string, client *http.Client) (*DeepSeek, error) {
	baseURL = strings.TrimSpace(baseURL)
	if baseURL == "" {
		baseURL = config.DeepSeekBaseURL
	}
	if strings.TrimSpace(model) == "" {
		model = config.DefaultDeepSeekModel
	}
	if client == nil {
		client = http.DefaultClient
	}
	return &DeepSeek{
		baseURL:    strings.TrimRight(baseURL, "/"),
		apiKey:     strings.TrimSpace(apiKey),
		model:      strings.TrimSpace(model),
		httpClient: client,
	}, nil
}

func (d *DeepSeek) endpoint() string {
	return chatURL(d.baseURL)
}

func (d *DeepSeek) setAuth(req *http.Request) {
	if d.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+d.apiKey)
	}
}

// Chat 执行同步对话调用
func (d *DeepSeek) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	httpReq, err := buildHTTPRequest(ctx, d.endpoint(), d.model, req, false)
	if err != nil {
		return nil, err
	}
	d.setAuth(httpReq)

	resp, err := d.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("deepseek: http error: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("deepseek: read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("deepseek: status %d: %s", resp.StatusCode, string(body))
	}

	content, toolCalls, usage, err := parseResponse(body)
	if err != nil {
		return nil, fmt.Errorf("deepseek: %w", err)
	}

	d.mu.Lock()
	d.totalUsage.Add(usage)
	d.mu.Unlock()

	return &ChatResponse{Content: content, ToolCalls: toolCalls, Usage: usage}, nil
}

// ChatStream 执行流式调用，支持深度思考链流式输出
func (d *DeepSeek) ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error) {
	httpReq, err := buildHTTPRequest(ctx, d.endpoint(), d.model, req, true)
	if err != nil {
		return nil, err
	}
	d.setAuth(httpReq)

	resp, err := d.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("deepseek: http stream error: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		return nil, fmt.Errorf("deepseek: stream status %d: %s", resp.StatusCode, string(body))
	}

	out := make(chan StreamChunk, 32)
	go func() {
		defer resp.Body.Close()
		defer close(out)
		usage := readSSE(ctx, resp.Body, out)
		if usage.TotalTokens > 0 {
			d.mu.Lock()
			d.totalUsage.Add(usage)
			d.mu.Unlock()
		}
	}()

	return out, nil
}

// TotalUsage 获取累计 Token 用量
func (d *DeepSeek) TotalUsage() Usage {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.totalUsage
}
