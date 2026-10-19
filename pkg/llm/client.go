package llm

import (
	"context"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
)

const (
	defaultDialTimeout           = 10 * time.Second
	defaultTLSHandshakeTimeout   = 10 * time.Second
	defaultResponseHeaderTimeout = 120 * time.Second
	defaultStreamHardLimit       = 10 * time.Minute
	defaultMaxRetries            = 3
)

// newTransportClient 构造带网络阶段超时的 HTTP 客户端
func newTransportClient() *http.Client {
	return &http.Client{
		Transport: &http.Transport{
			DialContext:           (&net.Dialer{Timeout: defaultDialTimeout}).DialContext,
			TLSHandshakeTimeout:   defaultTLSHandshakeTimeout,
			ResponseHeaderTimeout: defaultResponseHeaderTimeout,
		},
	}
}

// Client 统一大模型传输客户端（并发安全，不可变配置）
type Client struct {
	provider        Provider
	name            string
	baseURL         string
	apiKey          string
	model           string
	httpClient      *http.Client
	authHook        func(*http.Request)
	customHeaders   map[string]string
	maxRetries      int
	streamHardLimit time.Duration

	mu         sync.RWMutex
	totalUsage Usage
}

// New 创建大模型客户端实例。
// provider: 目标模型厂商（如 ProviderDeepSeek、ProviderGemini、ProviderSpark、ProviderLlamaCpp、ProviderCustom）
// opts: 可选配置参数（WithAPIKey, WithBaseURL, WithModel, WithHTTPClient, WithMaxRetries 等）
func New(provider Provider, opts ...Option) (*Client, error) {
	p := NormalizeProvider(provider)

	c := &Client{
		provider:        p,
		name:            string(p),
		baseURL:         DefaultBaseURL(p),
		model:           DefaultModel(p),
		httpClient:      newTransportClient(),
		maxRetries:      defaultMaxRetries,
		streamHardLimit: defaultStreamHardLimit,
	}

	// 应用外部传入的 Option
	for _, opt := range opts {
		if opt != nil {
			opt(c)
		}
	}

	c.baseURL = strings.TrimRight(strings.TrimSpace(c.baseURL), "/")
	if c.baseURL == "" {
		c.baseURL = DefaultBaseURL(p)
	}

	c.model = strings.TrimSpace(c.model)
	if c.model == "" {
		c.model = DefaultModel(p)
	}

	c.apiKey = strings.TrimSpace(c.apiKey)
	if c.apiKey == "" && !IsLocalProvider(p) {
		return nil, ErrEmptyAPIKey
	}

	// 若未显式注入自定义鉴权钩子，使用厂商默认规则
	if c.authHook == nil {
		c.authHook = defaultAuthHook(p, c.apiKey)
	}

	return c, nil
}

// Provider 返回绑定的厂商标识
func (c *Client) Provider() Provider {
	return c.provider
}

// BaseURL 返回绑定的服务根地址
func (c *Client) BaseURL() string {
	return c.baseURL
}

// Model 返回绑定的默认模型名
func (c *Client) Model() string {
	return c.model
}

func (c *Client) endpoint() string {
	return ResolveChatURL(c.baseURL)
}

// ChatStream 发起流式调用，返回只读事件通道。
// 内置网络抖动与 429/5xx 指数退避重试，调用方负责从返回通道读取增量。
// 当通道关闭时，底层的响应体必然已被关闭，绝不泄露连接。
func (c *Client) ChatStream(ctx context.Context, req *ChatRequest) (<-chan ChatResponse, error) {
	streamCtx, cancel := context.WithTimeout(ctx, c.streamHardLimit)
	resp, err := c.executeWithRetry(streamCtx, req)
	if err != nil {
		cancel()
		return nil, err
	}

	return c.pump(streamCtx, cancel, resp), nil
}

// Chat 一次性完整调用（内部复用流式并自动聚合文本、思考链与工具调用）。
// 适用于无需逐字打字机效果的后台批处理、分类汇总或脚本调用。
func (c *Client) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	stream, err := c.ChatStream(ctx, req)
	if err != nil {
		return nil, err
	}

	var (
		fullText      strings.Builder
		fullReasoning strings.Builder
		lastUsage     *Usage
		toolCalls     []ToolCall
	)

	for chunk := range stream {
		if chunk.Err != nil {
			return nil, chunk.Err
		}
		if chunk.Delta != "" {
			fullText.WriteString(chunk.Delta)
		}
		if chunk.ReasoningContent != "" {
			fullReasoning.WriteString(chunk.ReasoningContent)
		}
		if len(chunk.ToolCalls) > 0 {
			toolCalls = append(toolCalls, chunk.ToolCalls...)
		}
		if chunk.Usage != nil {
			lastUsage = chunk.Usage
		}
	}

	return &ChatResponse{
		Delta:            fullText.String(),
		ReasoningContent: fullReasoning.String(),
		ToolCalls:        toolCalls,
		Usage:            lastUsage,
		Done:             true,
	}, nil
}

// pump 独占响应体生命周期：通道关闭时 Body 必关闭、Context 必释放。
func (c *Client) pump(ctx context.Context, cancel context.CancelFunc, resp *http.Response) <-chan ChatResponse {
	out := make(chan ChatResponse, 32)

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

// executeWithRetry 执行 HTTP 请求并在遇到 429、5xx 或临时网络错误时自动指数退避重试
func (c *Client) executeWithRetry(ctx context.Context, req *ChatRequest) (*http.Response, error) {
	payload, err := BuildRequestPayload(c.model, req, true)
	if err != nil {
		return nil, err
	}

	maxAttempts := c.maxRetries
	if maxAttempts <= 0 {
		maxAttempts = 1
	}

	var lastErr error

	for attempt := 1; attempt <= maxAttempts; attempt++ {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		httpReq, err := buildHTTPRequest(ctx, c.endpoint(), payload, true)
		if err != nil {
			return nil, err
		}

		// 注入鉴权头
		if c.authHook != nil {
			c.authHook(httpReq)
		}

		// 注入自定义通用头
		for k, v := range c.customHeaders {
			httpReq.Header.Set(k, v)
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

// TotalUsage 获取当前实例累计消耗的总 Token 用量
func (c *Client) TotalUsage() Usage {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.totalUsage
}
