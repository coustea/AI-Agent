package gateway

import (
	"net/http"

	"my-agent/internal/config"
)

// DeepSeek 通过 DeepSeek 官方 API 调用模型，支持深度思考链 (reasoning_content)
type DeepSeek struct{ *compatClient }

// NewDeepSeek 创建 DeepSeek 网关实例
func NewDeepSeek(baseURL, apiKey, model string, client *http.Client) (*DeepSeek, error) {
	c, err := newCompatClient(compatOptions{
		name:           "deepseek",
		baseURL:        baseURL,
		apiKey:         apiKey,
		model:          model,
		defaultBaseURL: config.DeepSeekBaseURL,
		defaultModel:   config.DefaultDeepSeekModel,
		httpClient:     client,
		setAuth: func(req *http.Request, apiKey string) {
			req.Header.Set("Authorization", "Bearer "+apiKey)
		},
	})
	if err != nil {
		return nil, err
	}
	return &DeepSeek{c}, nil
}
