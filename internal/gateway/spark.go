package gateway

import (
	"net/http"

	"my-agent/internal/config"
)

// Spark 通过讯飞星辰 MaaS 平台 API 调用大模型
type Spark struct{ *compatClient }

// NewSpark 创建星辰 MaaS 网关实例
func NewSpark(baseURL, apiKey, model string, client *http.Client) (*Spark, error) {
	c, err := newCompatClient(compatOptions{
		name:           "spark",
		baseURL:        baseURL,
		apiKey:         apiKey,
		model:          model,
		defaultBaseURL: config.DefaultSparkBaseURL,
		defaultModel:   config.DefaultSparkModel,
		httpClient:     client,
		setAuth: func(req *http.Request, apiKey string) {
			req.Header.Set("Authorization", "Bearer "+apiKey)
		},
	})
	if err != nil {
		return nil, err
	}
	return &Spark{c}, nil
}
