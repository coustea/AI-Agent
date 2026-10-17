package gateway

import (
	"context"
	"fmt"
	"io"
	"net/http"

	"my-agent/internal/config"
)

// LlamaCpp 通过 llama-server 的 HTTP 服务调用本地模型
type LlamaCpp struct{ *compatClient }

// NewLlamaCpp 创建 llama.cpp 本地网关实例
func NewLlamaCpp(baseURL, apiKey, model string, client *http.Client) (*LlamaCpp, error) {
	c, err := newCompatClient(compatOptions{
		name:           "llamacpp",
		baseURL:        baseURL,
		apiKey:         apiKey,
		model:          model,
		defaultBaseURL: config.DefaultLlamaCppBaseURL,
		defaultModel:   config.DefaultLlamaCppModel,
		httpClient:     client,
		allowEmptyKey:  true,
		setAuth: func(req *http.Request, apiKey string) {
			if apiKey != "" {
				req.Header.Set("Authorization", "Bearer "+apiKey)
			}
		},
	})
	if err != nil {
		return nil, err
	}
	return &LlamaCpp{c}, nil
}

// CheckHealth 检查 llama-server 服务健康与模型加载状态
func (l *LlamaCpp) CheckHealth(ctx context.Context) error {
	url := l.baseURL + "/health"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return fmt.Errorf("llamacpp: create health request: %w", err)
	}

	resp, err := l.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("llamacpp: server unreachable at %s: %w", l.baseURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		return nil
	}
	if resp.StatusCode == http.StatusServiceUnavailable {
		return fmt.Errorf("llamacpp: server is still loading model (503 Service Unavailable)")
	}

	body, _ := io.ReadAll(resp.Body)
	return fmt.Errorf("llamacpp: health check status %d: %s", resp.StatusCode, string(body))
}
