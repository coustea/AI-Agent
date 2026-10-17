// Package gateway 定义统一的大模型网关抽象与 OpenAI wire 协议实现。
// 核心数据模型（Message/Role/ToolCall/ToolResult/ToolDefinition/Usage/ChatRequest/ChatResponse）
// 统一定义在 internal/protocol 契约层中，本包只负责协议传输与多厂商路由。
package gateway

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"

	"my-agent/internal/config"
	"my-agent/internal/protocol"
)

var (
	ErrEmptyAPIKey   = errors.New("gateway: api key cannot be empty")
	ErrEmptyMessages = errors.New("gateway: messages cannot be empty")
)

// Gateway 统一 AI 网关接口
type Gateway interface {
	// ChatStream 执行流式调用，逐个返回流式生成块与响应
	ChatStream(ctx context.Context, req *protocol.ChatRequest) (<-chan protocol.ChatResponse, error)

	// TotalUsage 获取当前网关实例累计消耗的总 Token 用量
	TotalUsage() protocol.Usage
}

// Client 是所有基于 OpenAI Chat Completions 协议厂商的统一传输客户端。
// 支持网络抖动与 429/5xx 指数退避重试，由 config 统一元数据驱动端点与鉴权规则。
type Client struct {
	provider   config.Provider
	name       string
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client
	auth       func(*http.Request)

	mu         sync.RWMutex
	totalUsage protocol.Usage
}

// NewClient 根据厂商标识创建统一的大模型网关客户端
func NewClient(provider config.Provider, baseURL, apiKey, model string, httpClient *http.Client) (*Client, error) {
	p := config.Provider(strings.ToLower(strings.TrimSpace(string(provider))))
	if p == "" {
		p = config.ProviderLlamaCpp
	}

	cleanBaseURL := strings.TrimSpace(baseURL)
	if cleanBaseURL == "" {
		cleanBaseURL = config.DefaultBaseURL(p)
	}

	cleanKey := strings.TrimSpace(apiKey)
	if cleanKey == "" && !config.IsLocalProvider(p) {
		return nil, ErrEmptyAPIKey
	}

	cleanModel := strings.TrimSpace(model)
	if cleanModel == "" {
		cleanModel = config.DefaultModel(p)
	}

	client := httpClient
	if client == nil {
		client = http.DefaultClient
	}

	c := &Client{
		provider:   p,
		name:       string(p),
		baseURL:    strings.TrimRight(cleanBaseURL, "/"),
		apiKey:     cleanKey,
		model:      cleanModel,
		httpClient: client,
	}

	switch p {
	case config.ProviderGemini:
		c.auth = func(req *http.Request) {
			req.Header.Set("Authorization", "Bearer "+c.apiKey)
			req.Header.Set("x-goog-api-key", c.apiKey)
		}
	default:
		c.auth = func(req *http.Request) {
			if c.apiKey != "" {
				req.Header.Set("Authorization", "Bearer "+c.apiKey)
			}
		}
	}

	return c, nil
}

// Provider 返回客户端所绑定的厂商标识
func (c *Client) Provider() config.Provider {
	return c.provider
}

// BaseURL 返回客户端所绑定的服务根地址
func (c *Client) BaseURL() string {
	return c.baseURL
}

// Model 返回客户端所绑定的默认模型名称
func (c *Client) Model() string {
	return c.model
}

// 便捷构造函数（针对具体厂商，委托给 NewClient）
func NewLlamaCpp(baseURL, apiKey, model string, client *http.Client) (*Client, error) {
	return NewClient(config.ProviderLlamaCpp, baseURL, apiKey, model, client)
}

func NewDeepSeek(baseURL, apiKey, model string, client *http.Client) (*Client, error) {
	return NewClient(config.ProviderDeepSeek, baseURL, apiKey, model, client)
}

func NewGemini(baseURL, apiKey, model string, client *http.Client) (*Client, error) {
	return NewClient(config.ProviderGemini, baseURL, apiKey, model, client)
}

func NewSpark(baseURL, apiKey, model string, client *http.Client) (*Client, error) {
	return NewClient(config.ProviderSpark, baseURL, apiKey, model, client)
}

// CheckHealth 检查服务端点健康与模型加载状态（如 llama-server 的 /health 端点）
func (c *Client) CheckHealth(ctx context.Context) error {
	url := c.baseURL + "/health"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return fmt.Errorf("%s: create health request: %w", c.name, err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("%s: server unreachable at %s: %w", c.name, c.baseURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		return nil
	}
	if resp.StatusCode == http.StatusServiceUnavailable {
		return fmt.Errorf("%s: server is still loading model (503 Service Unavailable)", c.name)
	}

	body, _ := io.ReadAll(resp.Body)
	return fmt.Errorf("%s: health check status %d: %s", c.name, resp.StatusCode, string(body))
}

func (c *Client) endpoint() string {
	return chatURL(c.baseURL)
}

// ChatStream 执行流式调用（内置网络抖动与 429/5xx 指数退避重试）
func (c *Client) ChatStream(ctx context.Context, req *protocol.ChatRequest) (<-chan protocol.ChatResponse, error) {
	resp, err := c.executeWithRetry(ctx, req)
	if err != nil {
		return nil, err
	}

	out := make(chan protocol.ChatResponse, 32)
	go func() {
		defer resp.Body.Close()
		defer close(out)
		usage := readSSE(ctx, resp.Body, out)
		if usage.TotalTokens > 0 {
			c.mu.Lock()
			c.totalUsage.Add(usage)
			c.mu.Unlock()
		}
	}()

	return out, nil
}

// executeWithRetry 执行 HTTP 请求并在遇到 429、5xx 或临时网络错误时自动指数退避重试（最多 3 次）
func (c *Client) executeWithRetry(ctx context.Context, req *protocol.ChatRequest) (*http.Response, error) {
	payload, err := buildRequestPayload(c.model, req, true)
	if err != nil {
		return nil, err
	}

	const maxAttempts = 3
	var lastErr error

	for attempt := 1; attempt <= maxAttempts; attempt++ {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		httpReq, err := buildHTTPRequestFromPayload(ctx, c.endpoint(), payload, true)
		if err != nil {
			return nil, err
		}
		if c.auth != nil {
			c.auth(httpReq)
		}

		resp, err := c.httpClient.Do(httpReq)
		if err != nil {
			lastErr = fmt.Errorf("%s: http stream error: %w", c.name, err)
			if attempt < maxAttempts && isRetryableNetworkError(err) {
				if waitErr := sleepBackoff(ctx, attempt); waitErr != nil {
					return nil, waitErr
				}
				continue
			}
			return nil, lastErr
		}

		if resp.StatusCode == http.StatusOK {
			return resp, nil
		}

		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		lastErr = fmt.Errorf("%s: stream status %d: %s", c.name, resp.StatusCode, string(body))

		// 429 (Rate Limit) 或 5xx (Server Error) 触发退避重试
		if attempt < maxAttempts && (resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= 500) {
			if waitErr := sleepBackoff(ctx, attempt); waitErr != nil {
				return nil, waitErr
			}
			continue
		}

		return nil, lastErr
	}

	return nil, lastErr
}

func isRetryableNetworkError(err error) bool {
	if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
		return false
	}
	return true
}

func sleepBackoff(ctx context.Context, attempt int) error {
	baseDelay := 150 * time.Millisecond
	delay := time.Duration(1<<(attempt-1)) * baseDelay
	timer := time.NewTimer(delay)
	defer timer.Stop()

	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

// TotalUsage 获取累计 Token 用量
func (c *Client) TotalUsage() protocol.Usage {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.totalUsage
}
