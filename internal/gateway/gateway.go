// Package gateway 定义统一的大模型网关抽象与 OpenAI wire 协议实现。
// 核心数据模型（Message/Role/ToolCall/ToolResult/ToolDefinition/Usage/ChatRequest/ChatResponse）
// 统一定义在 internal/protocol 契约层中，本包只负责协议传输与多厂商路由。
package gateway

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net"
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

// streamHardLimit 单次流式调用的整体兜底超时。
// 本地单用户场景取粗粒度：不做逐 chunk 空闲超时（需侵入连接层，收益不成比例）。
const streamHardLimit = 10 * time.Minute

// newTransportClient 构造带网络阶段超时的 HTTP 客户端（连接 10s / TLS 握手 10s / 首响应头 120s）。
// 响应体不设整体超时——由 ChatStream 的 streamHardLimit 统一兜底。
func newTransportClient() *http.Client {
	return &http.Client{
		Transport: &http.Transport{
			DialContext:           (&net.Dialer{Timeout: 10 * time.Second}).DialContext,
			TLSHandshakeTimeout:   10 * time.Second,
			ResponseHeaderTimeout: 120 * time.Second,
		},
	}
}

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
	cleanModel = config.NormalizeModelName(p, cleanModel)
	if cleanModel == "" {
		cleanModel = config.DefaultModel(p)
	}

	client := httpClient
	if client == nil {
		client = newTransportClient()
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

// NewGatewayFromConfig 根据配置直接构造对应厂商的传输客户端。
// 厂商切换由 CoreAgent.UpdateConfig 热装网关完成，无需路由层。
func NewGatewayFromConfig(cfg *config.Config) (Gateway, error) {
	if cfg == nil {
		return nil, fmt.Errorf("gateway: configuration cannot be nil")
	}
	// 显式判错：直接 return NewClient 会把 nil *Client 包成非 nil 接口，
	// 使上层"未就绪内核"判定失效
	c, err := NewClient(cfg.Provider, cfg.BaseURL, cfg.APIKey, cfg.ModelName, nil)
	if err != nil {
		return nil, err
	}
	return c, nil
}

func (c *Client) endpoint() string {
	return chatURL(c.baseURL)
}

// ChatStream 执行流式调用（内置网络抖动与 429/5xx 指数退避重试，整体受 streamHardLimit 兜底）
func (c *Client) ChatStream(ctx context.Context, req *protocol.ChatRequest) (<-chan protocol.ChatResponse, error) {
	streamCtx, cancel := context.WithTimeout(ctx, streamHardLimit)
	resp, err := c.executeWithRetry(streamCtx, req)
	if err != nil {
		cancel()
		return nil, err
	}

	return c.pump(streamCtx, cancel, resp), nil
}

// pump 独占响应体生命周期：返回的 channel 关闭时，Body 必已关闭、超时 context 必已释放。
// 把响应体所有权收敛在本函数内，调用方只消费 channel，不必关心资源释放。
func (c *Client) pump(ctx context.Context, cancel context.CancelFunc, resp *http.Response) <-chan protocol.ChatResponse {
	out := make(chan protocol.ChatResponse, 32)

	go func() {
		defer close(out)
		defer cancel()
		defer func() { _ = resp.Body.Close() }()

		usage := readSSE(ctx, resp.Body, out)
		if usage.TotalTokens > 0 {
			c.mu.Lock()
			c.totalUsage.Add(usage)
			c.mu.Unlock()
		}
	}()

	return out
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
