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
	defaultDialTimeout           = 10 * time.Second
	defaultTLSHandshakeTimeout   = 10 * time.Second
	defaultResponseHeaderTimeout = 120 * time.Second

	baseBackoff      = 300 * time.Millisecond
	maxBackoff       = 8 * time.Second
	maxRetryAfter    = 30 * time.Second
	maxErrorBodySize = 8 << 10
)

// newHTTPClient 构造带网络阶段超时的 HTTP 客户端。
// 必须显式声明 Proxy 与 ForceAttemptHTTP2：一旦自定义 Transport 而不设这两项，
// net/http 会静默丢弃 HTTP_PROXY 并降级到 HTTP/1.1。
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
	endpoint := c.spec.endpoint(c.baseURL)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("llm: 构造请求失败: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")
	c.spec.authorize(req, c.apiKey)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		// 取消与超时直接上抛，保持 errors.Is(err, context.Canceled) 可判定
		if ctxErr := ctx.Err(); ctxErr != nil {
			return nil, ctxErr
		}
		return nil, &APIError{Provider: Provider(c.spec.ID), URL: endpoint, Err: err}
	}

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return resp, nil
	}

	// 错误体必须限长读取：网关 502 时可能返回整页 HTML
	body, _ := io.ReadAll(io.LimitReader(resp.Body, maxErrorBodySize))
	_ = resp.Body.Close()

	return nil, &APIError{
		Provider:   Provider(c.spec.ID),
		URL:        endpoint,
		Status:     resp.StatusCode,
		Body:       strings.TrimSpace(string(body)),
		RetryAfter: parseRetryAfter(resp.Header.Get("Retry-After")),
	}
}

// backoffDelay 计算第 attempt 次失败后的等待时长：指数增长、封顶、带抖动。
// Retry-After 是上游的明确指令，单独按 maxRetryAfter 夹取。
func backoffDelay(attempt int, retryAfter time.Duration) time.Duration {
	if retryAfter > 0 {
		return min(retryAfter, maxRetryAfter)
	}

	delay := baseBackoff << (attempt - 1)
	if delay <= 0 || delay > maxBackoff {
		delay = maxBackoff
	}
	// ±25% 抖动，避免多请求同步重试
	jitter := time.Duration((rand.Float64() - 0.5) * 0.5 * float64(delay))
	return delay + jitter
}

// parseRetryAfter 支持 Retry-After 的两种格式：秒数与 HTTP 日期。
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

// sleepCtx 等待指定时长，可被 context 提前打断。
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
