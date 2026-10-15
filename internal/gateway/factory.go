package gateway

import (
	"fmt"
	"strings"

	"my-agent/internal/config"
)

// NewGatewayFromConfig 根据全局配置实例化对应的 AI 网关客户端
func NewGatewayFromConfig(cfg *config.Config) (Gateway, error) {
	if cfg == nil {
		return nil, fmt.Errorf("gateway: configuration cannot be nil")
	}

	model := strings.TrimSpace(cfg.ModelName)

	switch strings.ToLower(string(cfg.Provider)) {
	case "gemini", "google":
		baseURL := strings.TrimSpace(cfg.BaseURL)
		if baseURL == "" {
			baseURL = config.GeminiBaseURL
		}
		if model == "" {
			model = config.DefaultGeminiModel
		}
		if strings.TrimSpace(cfg.APIKey) == "" {
			return nil, ErrEmptyAPIKey
		}
		return NewLlamaCppGateway(baseURL, cfg.APIKey, model, nil)

	case "deepseek", "ds":
		baseURL := strings.TrimSpace(cfg.BaseURL)
		if baseURL == "" {
			baseURL = config.DeepSeekBaseURL
		}
		if model == "" {
			model = config.DefaultDeepSeekModel
		}
		return NewLlamaCppGateway(baseURL, cfg.APIKey, model, nil)

	case "llamacpp", "llama", "local", "":
		baseURL := strings.TrimSpace(cfg.BaseURL)
		if baseURL == "" {
			baseURL = config.DefaultLlamaCppBaseURL
		}
		if model == "" {
			model = config.DefaultLlamaCppModel
		}
		return NewLlamaCppGateway(baseURL, cfg.APIKey, model, nil)

	default:
		return nil, fmt.Errorf("gateway: unsupported provider %q", cfg.Provider)
	}
}
