package gateway

import (
	"net/http"

	"my-agent/internal/config"
)

// Gemini 通过 Google 官方 OpenAI 兼容端点调用 Gemini 模型
type Gemini struct{ *compatClient }

// NewGemini 创建 Gemini 网关实例
func NewGemini(baseURL, apiKey, model string, client *http.Client) (*Gemini, error) {
	c, err := newCompatClient(compatOptions{
		name:           "gemini",
		baseURL:        baseURL,
		apiKey:         apiKey,
		model:          model,
		defaultBaseURL: config.GeminiBaseURL,
		defaultModel:   config.DefaultGeminiModel,
		httpClient:     client,
		setAuth: func(req *http.Request, apiKey string) {
			req.Header.Set("Authorization", "Bearer "+apiKey)
			req.Header.Set("x-goog-api-key", apiKey)
		},
	})
	if err != nil {
		return nil, err
	}
	return &Gemini{c}, nil
}
