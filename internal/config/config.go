package config

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
)

// Provider 定义支持的模型厂商
type Provider string

const (
	ProviderLlamaCpp Provider = "llamacpp"
	ProviderDeepSeek Provider = "deepseek"
	ProviderGemini   Provider = "gemini"
)

// 默认模型与服务端点推荐
const (
	// llama.cpp 本地 HTTP 服务默认配置
	DefaultLlamaCppBaseURL = "http://127.0.0.1:8080"
	DefaultLlamaCppModel   = "local-model"

	// DeepSeek 官方最新模型规范 (V4 系列)
	DefaultDeepSeekModel = "deepseek-flash"
	DeepSeekProModel     = "deepseek-v4-pro"
	DeepSeekBaseURL      = "https://api.deepseek.com"

	// Google Gemini 官方最新模型规范 (兼容 OpenAI 协议端点)
	DefaultGeminiModel = "gemini-2.5-flash"
	GeminiProModel     = "gemini-2.5-pro"
	GeminiBaseURL      = "https://generativelanguage.googleapis.com/v1beta/openai"
)

// Config 保存应用的基础模型配置
type Config struct {
	Provider  Provider `json:"provider"`           // "llamacpp", "deepseek", "gemini"
	BaseURL   string   `json:"base_url,omitempty"` // 服务端点地址
	ModelName string   `json:"model_name"`         // 具体模型名称
	APIKey    string   `json:"api_key,omitempty"`  // API 密钥 (本地 llama.cpp 可留空，云端必填)
}

// DefaultConfigPath 返回默认配置文件路径（当前工作目录下的 config.json）
func DefaultConfigPath() string {
	return "config.json"
}

// LoadConfig 从指定 JSON 文件加载配置，支持环境变量自动发现
func LoadConfig(path string) (*Config, error) {
	if path == "" {
		path = DefaultConfigPath()
	}

	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			// 优先根据环境变量自动创建推荐配置
			if deepseekKey := strings.TrimSpace(os.Getenv("DEEPSEEK_API_KEY")); deepseekKey != "" {
				return &Config{
					Provider:  ProviderDeepSeek,
					BaseURL:   DeepSeekBaseURL,
					ModelName: DefaultDeepSeekModel,
					APIKey:    deepseekKey,
				}, nil
			}

			if geminiKey := strings.TrimSpace(os.Getenv("GEMINI_API_KEY")); geminiKey != "" {
				return &Config{
					Provider:  ProviderGemini,
					BaseURL:   GeminiBaseURL,
					ModelName: DefaultGeminiModel,
					APIKey:    geminiKey,
				}, nil
			}

			if googleKey := strings.TrimSpace(os.Getenv("GOOGLE_API_KEY")); googleKey != "" {
				return &Config{
					Provider:  ProviderGemini,
					BaseURL:   GeminiBaseURL,
					ModelName: DefaultGeminiModel,
					APIKey:    googleKey,
				}, nil
			}

			// 默认使用本地 llama.cpp 配置
			return &Config{
				Provider:  ProviderLlamaCpp,
				BaseURL:   DefaultLlamaCppBaseURL,
				ModelName: DefaultLlamaCppModel,
			}, nil
		}
		return nil, err
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	if cfg.Provider == "" {
		cfg.Provider = ProviderLlamaCpp
	}

	// 若配置中 APIKey 为空，尝试从环境变量自动补全
	if cfg.APIKey == "" {
		switch strings.ToLower(string(cfg.Provider)) {
		case "deepseek", "ds":
			cfg.APIKey = strings.TrimSpace(os.Getenv("DEEPSEEK_API_KEY"))
		case "gemini", "google":
			cfg.APIKey = strings.TrimSpace(os.Getenv("GEMINI_API_KEY"))
			if cfg.APIKey == "" {
				cfg.APIKey = strings.TrimSpace(os.Getenv("GOOGLE_API_KEY"))
			}
		}
	}

	// 针对远程云端服务要求必填 APIKey，本地 llamacpp 可不填 APIKey
	if !IsLocalProvider(cfg.Provider) && cfg.APIKey == "" {
		return nil, errors.New("incomplete config: api_key is required for remote provider")
	}

	return &cfg, nil
}

// IsLocalProvider 判断是否为无需鉴权的本地服务提供商
func IsLocalProvider(p Provider) bool {
	switch strings.ToLower(string(p)) {
	case "llamacpp", "llama", "local":
		return true
	default:
		return false
	}
}

// SaveConfig 将配置持久化为格式化的 JSON 文件
func SaveConfig(path string, cfg *Config) error {
	if path == "" {
		path = DefaultConfigPath()
	}

	dir := filepath.Dir(path)
	if dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(path, data, 0o600)
}

// GetDefaultModelForProvider 根据厂商返回最新默认模型名称
func GetDefaultModelForProvider(p Provider) string {
	switch strings.ToLower(string(p)) {
	case "gemini", "google":
		return DefaultGeminiModel
	case "deepseek", "ds":
		return DefaultDeepSeekModel
	case "llamacpp", "llama", "local":
		fallthrough
	default:
		return DefaultLlamaCppModel
	}
}

// GetDefaultBaseURLForProvider 根据厂商返回默认服务端点
func GetDefaultBaseURLForProvider(p Provider) string {
	switch strings.ToLower(string(p)) {
	case "gemini", "google":
		return GeminiBaseURL
	case "deepseek", "ds":
		return DeepSeekBaseURL
	case "llamacpp", "llama", "local":
		fallthrough
	default:
		return DefaultLlamaCppBaseURL
	}
}
