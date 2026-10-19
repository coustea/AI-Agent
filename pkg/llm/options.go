package llm

import (
	"net/http"
	"time"
)

// Option 定义客户端函数式配置选项
type Option func(*Client)

// WithBaseURL 设置模型服务根地址（若末尾不含路径，将智能适配 /chat/completions）
func WithBaseURL(url string) Option {
	return func(c *Client) {
		c.baseURL = url
	}
}

// WithAPIKey 设置模型调用凭据
func WithAPIKey(key string) Option {
	return func(c *Client) {
		c.apiKey = key
	}
}

// WithModel 设置调用的默认具体模型名称
func WithModel(model string) Option {
	return func(c *Client) {
		c.model = model
	}
}

// WithHTTPClient 注入自定义底层 HTTP 客户端（例如带有定制连接池、代理或追踪中间件）
func WithHTTPClient(client *http.Client) Option {
	return func(c *Client) {
		if client != nil {
			c.httpClient = client
		}
	}
}

// WithMaxRetries 设置遇到临时网络抖动、429 (限流) 或 5xx (服务不可用) 时的最大重试次数
func WithMaxRetries(retries int) Option {
	return func(c *Client) {
		if retries >= 0 {
			c.maxRetries = retries
		}
	}
}

// WithStreamTimeout 设置流式调用的整体超时上限（默认 10 分钟）
func WithStreamTimeout(timeout time.Duration) Option {
	return func(c *Client) {
		if timeout > 0 {
			c.streamHardLimit = timeout
		}
	}
}

// WithHeader 设置自定义通用 HTTP 请求头（如自建代理鉴权、自定义 Org ID 等）
func WithHeader(key, value string) Option {
	return func(c *Client) {
		if c.customHeaders == nil {
			c.customHeaders = make(map[string]string)
		}
		c.customHeaders[key] = value
	}
}

// WithAuthHook 自定义请求鉴权注入逻辑（覆盖默认的 Authorization Header 注入）
func WithAuthHook(hook func(*http.Request)) Option {
	return func(c *Client) {
		if hook != nil {
			c.authHook = hook
		}
	}
}
