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

	"my-agent/internal/protocol"
)

// compatClient 是所有走 OpenAI Chat Completions 协议厂商的共享传输实现。
// 各厂商仅通过 compatOptions（错误前缀、鉴权头、默认端点/模型、是否允许空密钥）体现差异，
// 避免在 deepseek/gemini/spark/llamacpp 间复制粘贴同一套 HTTP/SSE 管道。
type compatClient struct {
	name       string
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client
	auth       func(*http.Request)

	mu         sync.RWMutex
	totalUsage protocol.Usage
}

// compatOptions 描述一个 OpenAI 兼容厂商的差异配置。
type compatOptions struct {
	name           string
	baseURL        string
	apiKey         string
	model          string
	defaultBaseURL string
	defaultModel   string
	httpClient     *http.Client
	allowEmptyKey  bool
	setAuth        func(req *http.Request, apiKey string)
}

// newCompatClient 归一化构造参数并构建共享客户端。
func newCompatClient(o compatOptions) (*compatClient, error) {
	baseURL := strings.TrimSpace(o.baseURL)
	if baseURL == "" {
		baseURL = o.defaultBaseURL
	}
	apiKey := strings.TrimSpace(o.apiKey)
	if apiKey == "" && !o.allowEmptyKey {
		return nil, ErrEmptyAPIKey
	}
	modelName := strings.TrimSpace(o.model)
	if modelName == "" {
		modelName = o.defaultModel
	}
	client := o.httpClient
	if client == nil {
		client = http.DefaultClient
	}

	c := &compatClient{
		name:       o.name,
		baseURL:    strings.TrimRight(baseURL, "/"),
		apiKey:     apiKey,
		model:      modelName,
		httpClient: client,
	}
	if o.setAuth != nil {
		c.auth = func(req *http.Request) { o.setAuth(req, apiKey) }
	}
	return c, nil
}

func (c *compatClient) endpoint() string {
	return chatURL(c.baseURL)
}

// ChatStream 执行流式调用（内置网络抖动与 429/5xx 指数退避重试）
func (c *compatClient) ChatStream(ctx context.Context, req *protocol.ChatRequest) (<-chan protocol.ChatResponse, error) {
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
func (c *compatClient) executeWithRetry(ctx context.Context, req *protocol.ChatRequest) (*http.Response, error) {
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
func (c *compatClient) TotalUsage() protocol.Usage {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.totalUsage
}
