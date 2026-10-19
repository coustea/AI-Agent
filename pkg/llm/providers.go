package llm

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// Provider 定义模型厂商标识
type Provider string

const (
	ProviderLlamaCpp Provider = "llamacpp"
	ProviderDeepSeek Provider = "deepseek"
	ProviderGemini   Provider = "gemini"
	ProviderSpark    Provider = "spark"
	ProviderOpenAI   Provider = "openai"
	ProviderCustom   Provider = "custom"
)

// 各主流厂商默认端点与推荐默认模型
const (
	DefaultLlamaCppBaseURL = "http://127.0.0.1:8080"
	DefaultLlamaCppModel   = "local-model"

	DefaultDeepSeekBaseURL = "https://api.deepseek.com"
	DefaultDeepSeekModel   = "deepseek-flash"

	DefaultGeminiBaseURL = "https://generativelanguage.googleapis.com/v1beta/openai"
	DefaultGeminiModel   = "gemini-2.5-flash"

	DefaultSparkBaseURL = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
	DefaultSparkModel   = "spark-x2.5-4b"

	DefaultOpenAIBaseURL = "https://api.openai.com/v1"
	DefaultOpenAIModel   = "gpt-4o"
)

// NormalizeProvider 规范化厂商名称（支持常用快捷别名）
func NormalizeProvider(p Provider) Provider {
	s := strings.ToLower(strings.TrimSpace(string(p)))
	switch s {
	case "llama", "local", "llamacpp":
		return ProviderLlamaCpp
	case "ds", "deepseek":
		return ProviderDeepSeek
	case "google", "gemini":
		return ProviderGemini
	case "maas", "xfyun", "spark":
		return ProviderSpark
	case "openai":
		return ProviderOpenAI
	case "custom":
		return ProviderCustom
	default:
		if s == "" {
			return ProviderLlamaCpp
		}
		return Provider(s)
	}
}

// DefaultBaseURL 获取厂商的默认服务根地址
func DefaultBaseURL(p Provider) string {
	switch NormalizeProvider(p) {
	case ProviderDeepSeek:
		return DefaultDeepSeekBaseURL
	case ProviderGemini:
		return DefaultGeminiBaseURL
	case ProviderSpark:
		return DefaultSparkBaseURL
	case ProviderOpenAI:
		return DefaultOpenAIBaseURL
	case ProviderLlamaCpp:
		return DefaultLlamaCppBaseURL
	default:
		return DefaultLlamaCppBaseURL
	}
}

// DefaultModel 获取厂商的默认推荐模型
func DefaultModel(p Provider) string {
	switch NormalizeProvider(p) {
	case ProviderDeepSeek:
		return DefaultDeepSeekModel
	case ProviderGemini:
		return DefaultGeminiModel
	case ProviderSpark:
		return DefaultSparkModel
	case ProviderOpenAI:
		return DefaultOpenAIModel
	case ProviderLlamaCpp:
		return DefaultLlamaCppModel
	default:
		return DefaultLlamaCppModel
	}
}

// IsLocalProvider 判断是否为无需鉴权的本地模型服务
func IsLocalProvider(p Provider) bool {
	return NormalizeProvider(p) == ProviderLlamaCpp
}

// defaultAuthHook 返回对应厂商的默认 HTTP 鉴权注入逻辑
func defaultAuthHook(p Provider, apiKey string) func(*http.Request) {
	cleanKey := strings.TrimSpace(apiKey)
	norm := NormalizeProvider(p)

	switch norm {
	case ProviderGemini:
		return func(req *http.Request) {
			if cleanKey != "" {
				req.Header.Set("Authorization", "Bearer "+cleanKey)
				req.Header.Set("x-goog-api-key", cleanKey)
			}
		}
	default:
		return func(req *http.Request) {
			if cleanKey != "" {
				req.Header.Set("Authorization", "Bearer "+cleanKey)
			}
		}
	}
}

// ProbeLocalService 探测本地模型服务（如 llama.cpp）是否就绪（默认 2s 超时）。
// 若服务正常响应 HTTP 200 则返回 nil，否则返回具体错误。
func ProbeLocalService(ctx context.Context, baseURL string) error {
	if ctx == nil {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
	}
	clean := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if clean == "" {
		clean = DefaultLlamaCppBaseURL
	}
	endpoint := clean + "/v1/models"

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, http.NoBody)
	if err != nil {
		return err
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status %d", resp.StatusCode)
	}
	return nil
}
