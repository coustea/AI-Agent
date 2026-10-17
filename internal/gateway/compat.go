package gateway

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"

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

// ChatStream 执行流式调用
func (c *compatClient) ChatStream(ctx context.Context, req *protocol.ChatRequest) (<-chan protocol.ChatResponse, error) {
	httpReq, err := buildHTTPRequest(ctx, c.endpoint(), c.model, req, true)
	if err != nil {
		return nil, err
	}
	if c.auth != nil {
		c.auth(httpReq)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("%s: http stream error: %w", c.name, err)
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		return nil, fmt.Errorf("%s: stream status %d: %s", c.name, resp.StatusCode, string(body))
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

// TotalUsage 获取累计 Token 用量
func (c *compatClient) TotalUsage() protocol.Usage {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.totalUsage
}
