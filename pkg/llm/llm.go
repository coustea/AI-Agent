// Package llm 提供面向标准 OpenAI 兼容协议（Chat Completions + SSE）的统一调用能力。
//
// 本包只依赖标准库，零外部依赖。通过 BaseURL + APIKey + Model 即可直连任意兼容端点
// （包括 OpenAI、DeepSeek、Moonshot、通义千问、vLLM、Ollama、LocalAI、Gemini 等）。
package llm

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"math/rand/v2"
	"net"
	"net/http"
	"strconv"
	"strings"
	"time"
)

const (
	defaultAttempts              = 3
	defaultStreamTimeout         = 10 * time.Minute
	defaultDialTimeout           = 10 * time.Second
	defaultTLSHandshakeTimeout   = 10 * time.Second
	defaultResponseHeaderTimeout = 120 * time.Second

	baseBackoff      = 300 * time.Millisecond
	maxBackoff       = 8 * time.Second
	maxRetryAfter    = 30 * time.Second
	maxErrorBodySize = 8 << 10
)

// ============================================================================
// Client 核心与生命周期
// ============================================================================

// Client 是面向 OpenAI 兼容服务的无状态调用客户端，可并发复用。
type Client struct {
	endpoint   string // 预计算并缓存的完整 chat completions URL
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client
	attempts   int
	timeout    time.Duration
}

// New 创建 OpenAI 兼容客户端。
func New(cfg Config) (*Client, error) {
	baseURL := strings.TrimRight(strings.TrimSpace(cfg.BaseURL), "/")
	if baseURL == "" {
		return nil, ErrEmptyBaseURL
	}

	model := strings.TrimSpace(cfg.Model)
	httpClient := cfg.HTTPClient
	if httpClient == nil {
		httpClient = newHTTPClient()
	}

	attempts := cfg.Attempts
	if attempts <= 0 {
		attempts = defaultAttempts
	}

	timeout := cfg.Timeout
	if timeout <= 0 {
		timeout = defaultStreamTimeout
	}

	return &Client{
		endpoint:   resolveEndpoint(baseURL),
		baseURL:    baseURL,
		apiKey:     strings.TrimSpace(cfg.APIKey),
		model:      model,
		httpClient: httpClient,
		attempts:   attempts,
		timeout:    timeout,
	}, nil
}

// resolveEndpoint 智能规范化 chat completions 请求端点。
func resolveEndpoint(baseURL string) string {
	base := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if strings.HasSuffix(base, "/chat/completions") {
		return base
	}
	if strings.HasSuffix(base, "/v1") {
		return base + "/chat/completions"
	}
	// 若路径已显式带版本（如 /v1beta/openai 或 /v2），直接拼装 /chat/completions
	if strings.Contains(base, "/v") {
		return base + "/chat/completions"
	}
	return base + "/v1/chat/completions"
}

// BaseURL 返回服务根地址。
func (c *Client) BaseURL() string { return c.baseURL }

// Model 返回默认模型名。
func (c *Client) Model() string { return c.model }

// Endpoint 返回生效的完整请求地址。
func (c *Client) Endpoint() string { return c.endpoint }

// ChatStream 发起流式调用。
//
// 返回的通道遵循 Chunk 上声明的四条不变量：终块恰好一次且在最后，
// Err != nil 当且仅当异常终止，通道关闭时响应体与 Context 必然已释放。
func (c *Client) ChatStream(ctx context.Context, req Request) (<-chan Chunk, error) {
	if ctx == nil {
		ctx = context.Background()
	}

	payload, err := encodeRequest(c.model, req)
	if err != nil {
		return nil, err
	}

	streamCtx, cancel := context.WithTimeout(ctx, c.timeout)
	resp, err := c.do(streamCtx, payload)
	if err != nil {
		cancel()
		return nil, err
	}

	return pump(streamCtx, cancel, resp), nil
}

// Chat 发起非流式同步调用，内部消费流并将增量累加到终块返回。
// 返回的 Chunk 中 Delta 为完整正文，Usage 为完整用量，ToolCalls 为完整工具调用列表。
func (c *Client) Chat(ctx context.Context, req Request) (Chunk, error) {
	stream, err := c.ChatStream(ctx, req)
	if err != nil {
		return Chunk{}, err
	}

	var last Chunk
	var text, reasoning strings.Builder
	for chunk := range stream {
		if chunk.Terminal() {
			last = chunk
			break
		}
		text.WriteString(chunk.Delta)
		reasoning.WriteString(chunk.ReasoningContent)
	}

	last.Delta = text.String()
	last.ReasoningContent = reasoning.String()
	return last, last.Err
}

// ============================================================================
// HTTP 传输与退避重试
// ============================================================================

func newHTTPClient() *http.Client {
	return &http.Client{
		Transport: &http.Transport{
			Proxy:                 http.ProxyFromEnvironment,
			ForceAttemptHTTP2:     true,
			DialContext:           (&net.Dialer{Timeout: defaultDialTimeout, KeepAlive: 30 * time.Second}).DialContext,
			TLSHandshakeTimeout:   defaultTLSHandshakeTimeout,
			ResponseHeaderTimeout: defaultResponseHeaderTimeout,
			MaxIdleConns:          16,
			MaxIdleConnsPerHost:   8,
			IdleConnTimeout:       90 * time.Second,
		},
	}
}

// do 发起请求并在可重试错误上退避重试，只返回 2xx 响应。
func (c *Client) do(ctx context.Context, payload []byte) (*http.Response, error) {
	var lastErr error

	for attempt := 1; attempt <= c.attempts; attempt++ {
		if err := ctx.Err(); err != nil {
			return nil, err
		}

		resp, err := c.attempt(ctx, payload)
		if err == nil {
			return resp, nil
		}
		lastErr = err

		var apiErr *APIError
		if !errors.As(err, &apiErr) || !apiErr.Retryable() || attempt == c.attempts {
			return nil, err
		}
		if err := sleepCtx(ctx, backoffDelay(attempt, apiErr.RetryAfter)); err != nil {
			return nil, err
		}
	}

	return nil, lastErr
}

// attempt 执行一次完整的 HTTP 往返。
func (c *Client) attempt(ctx context.Context, payload []byte) (*http.Response, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint, bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("llm: 构造请求失败: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")
	if c.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.apiKey)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		if ctxErr := ctx.Err(); ctxErr != nil {
			return nil, ctxErr
		}
		return nil, &APIError{URL: c.endpoint, Err: err}
	}

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return resp, nil
	}

	// 错误体限长读取
	body, _ := io.ReadAll(io.LimitReader(resp.Body, maxErrorBodySize))
	_ = resp.Body.Close()

	return nil, &APIError{
		URL:        c.endpoint,
		Status:     resp.StatusCode,
		Body:       strings.TrimSpace(string(body)),
		RetryAfter: parseRetryAfter(resp.Header.Get("Retry-After")),
	}
}

// backoffDelay 计算第 attempt 次失败后的等待时长：指数增长、封顶、带抖动。
func backoffDelay(attempt int, retryAfter time.Duration) time.Duration {
	if retryAfter > 0 {
		return min(retryAfter, maxRetryAfter)
	}

	delay := baseBackoff << (attempt - 1)
	if delay <= 0 || delay > maxBackoff {
		delay = maxBackoff
	}
	// ±25% 抖动
	jitter := time.Duration((rand.Float64() - 0.5) * 0.5 * float64(delay))
	return delay + jitter
}

func parseRetryAfter(raw string) time.Duration {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return 0
	}
	if seconds, err := strconv.Atoi(raw); err == nil {
		if seconds <= 0 {
			return 0
		}
		return time.Duration(seconds) * time.Second
	}
	if when, err := http.ParseTime(raw); err == nil {
		if wait := time.Until(when); wait > 0 {
			return wait
		}
	}
	return 0
}

func sleepCtx(ctx context.Context, d time.Duration) error {
	if d <= 0 {
		return nil
	}
	timer := time.NewTimer(d)
	defer timer.Stop()

	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}
