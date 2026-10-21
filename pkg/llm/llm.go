// Package llm 提供面向通用大模型（OpenAI 兼容端点及 DeepSeek、Gemini、Spark、llama.cpp 等预设）的统一调用能力。
//
// 本包只依赖标准库，可直接整包复制到其他项目。
// 支持仅传入 APIKey、BaseURL、Model 接入任意兼容服务，也支持通过 Provider 使用预设厂商。
package llm

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"
)

const (
	defaultAttempts      = 3
	defaultStreamTimeout = 10 * time.Minute
)

// Config 是创建 Client 的全部输入。
// 支持仅提供 APIKey + BaseURL + Model 直连兼容端点；亦可指定 Provider 使用预设厂商默认值。
type Config struct {
	Provider   Provider      // 厂商标识；空且提供 BaseURL 时默认为通用 OpenAI 兼容端点
	APIKey     string        // 远程端点必填；本地端点可空
	BaseURL    string        // 服务根地址（自动兼容 /v1、/chat/completions 等后缀）
	Model      string        // 默认模型名
	HTTPClient *http.Client  // 空 = 内置客户端
	Timeout    time.Duration // 空 = 10 分钟（整次流式调用硬超时）
	Attempts   int           // 0 = 默认 3 次；1 = 不重试
}

// Client 是绑定单一厂商与模型的无状态调用客户端，可并发复用。
type Client struct {
	spec       Spec
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client
	attempts   int
	timeout    time.Duration
}

// New 按 Config 创建客户端。
// 支持显式指定预设厂商，也支持仅传入 APIKey、BaseURL、Model 接入任意 OpenAI 兼容端点。
func New(cfg Config) (*Client, error) {
	canonical := Provider(strings.ToLower(strings.TrimSpace(string(cfg.Provider))))
	spec, ok := Lookup(canonical)
	if !ok {
		baseURL := strings.TrimRight(strings.TrimSpace(cfg.BaseURL), "/")
		if baseURL == "" {
			return nil, fmt.Errorf("%w: %q", ErrUnknownProvider, cfg.Provider)
		}
		if canonical == "" {
			canonical = ProviderOpenAI
		}
		spec = Spec{
			ID:           canonical,
			BaseURL:      baseURL,
			ChatPath:     "/v1/chat/completions",
			DefaultModel: strings.TrimSpace(cfg.Model),
			Auth:         AuthBearer,
			Local:        isLocalBaseURL(baseURL),
		}
	}

	apiKey := strings.TrimSpace(cfg.APIKey)
	if apiKey == "" && !spec.Local {
		return nil, ErrNoAPIKey
	}

	baseURL := strings.TrimRight(strings.TrimSpace(cfg.BaseURL), "/")
	if baseURL == "" {
		baseURL = spec.BaseURL
	}

	model := strings.TrimSpace(cfg.Model)
	if model == "" {
		model = spec.DefaultModel
	}

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
		spec:       spec,
		baseURL:    baseURL,
		apiKey:     apiKey,
		model:      model,
		httpClient: httpClient,
		attempts:   attempts,
		timeout:    timeout,
	}, nil
}

func isLocalBaseURL(u string) bool {
	return strings.Contains(u, "127.0.0.1") || strings.Contains(u, "localhost") || strings.Contains(u, "::1")
}

// Provider 返回绑定的厂商标识。
func (c *Client) Provider() Provider { return c.spec.ID }

// BaseURL 返回生效的服务根地址。
func (c *Client) BaseURL() string { return c.baseURL }

// Model 返回生效的模型名。
func (c *Client) Model() string { return c.model }

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
