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

// ProviderConfig 保存各厂商的专属模型与密钥配置
type ProviderConfig struct {
	BaseURL   string `json:"base_url,omitempty"`   // 服务端点地址
	ModelName string `json:"model_name,omitempty"` // 模型名称
	APIKey    string `json:"api_key,omitempty"`    // API 密钥
}

// Config 保存应用的基础模型配置及多厂商独立持久化配置
type Config struct {
	Provider  Provider                  `json:"provider"`            // 当前激活的模型厂商
	BaseURL   string                    `json:"base_url,omitempty"`  // 当前激活的服务端点地址
	ModelName string                    `json:"model_name"`          // 当前激活的具体模型名称
	APIKey    string                    `json:"api_key,omitempty"`   // 当前激活的 API 密钥
	Providers map[string]ProviderConfig `json:"providers,omitempty"` // 各厂商独立保存的配置历史
}

// GlobalConfigDir 返回用户级全局配置目录 (~/.coustea)
func GlobalConfigDir() string {
	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		return "."
	}
	return filepath.Join(home, ".coustea")
}

// GlobalConfigPath 返回用户级全局配置文件路径 (~/.coustea/config.json)
func GlobalConfigPath() string {
	return filepath.Join(GlobalConfigDir(), "config.json")
}

// ResolveConfigPath 解析生效的配置文件路径：
// 1. 若指定了非空 path，优先使用指定的 path；
// 2. 若当前工作目录下存在 config.json，优先使用当前项目目录的本地配置；
// 3. 否则默认使用用户主目录下的全局配置 (~/.coustea/config.json)。
func ResolveConfigPath(path string) string {
	if strings.TrimSpace(path) != "" {
		return strings.TrimSpace(path)
	}

	localPath := "config.json"
	if _, err := os.Stat(localPath); err == nil {
		return localPath
	}

	return GlobalConfigPath()
}

// DefaultConfigPath 返回默认配置文件路径
func DefaultConfigPath() string {
	return ResolveConfigPath("")
}

// normalizeProviderKey 标准化厂商标识 key
func normalizeProviderKey(p Provider) string {
	key := strings.ToLower(string(p))
	switch key {
	case "llama", "local":
		return "llamacpp"
	case "ds":
		return "deepseek"
	case "google":
		return "gemini"
	default:
		return key
	}
}

// GetProviderConfig 获取指定厂商已保存的配置
func (c *Config) GetProviderConfig(p Provider) ProviderConfig {
	if c == nil || c.Providers == nil {
		return ProviderConfig{}
	}
	return c.Providers[normalizeProviderKey(p)]
}

// SetProviderConfig 记录并更新指定厂商的专属配置
func (c *Config) SetProviderConfig(p Provider, pcfg ProviderConfig) {
	if c.Providers == nil {
		c.Providers = make(map[string]ProviderConfig)
	}
	c.Providers[normalizeProviderKey(p)] = pcfg
}

// SwitchProvider 切换当前激活的厂商，并自动载入该厂商已保存的配置历史
func (c *Config) SwitchProvider(p Provider) {
	c.Provider = p
	pcfg := c.GetProviderConfig(p)

	if pcfg.BaseURL != "" {
		c.BaseURL = pcfg.BaseURL
	} else {
		c.BaseURL = GetDefaultBaseURLForProvider(p)
	}

	if pcfg.ModelName != "" {
		c.ModelName = pcfg.ModelName
	} else {
		c.ModelName = GetDefaultModelForProvider(p)
	}

	if pcfg.APIKey != "" {
		c.APIKey = pcfg.APIKey
	}
}

// LoadConfig 从指定 JSON 文件加载配置，支持全局/本地发现与环境变量自动补全
func LoadConfig(path string) (*Config, error) {
	resolvedPath := ResolveConfigPath(path)

	data, err := os.ReadFile(resolvedPath)
	if err != nil {
		if os.IsNotExist(err) {
			cfg := &Config{
				Providers: make(map[string]ProviderConfig),
			}

			// 收集环境变量中的密钥
			if dsKey := strings.TrimSpace(os.Getenv("DEEPSEEK_API_KEY")); dsKey != "" {
				cfg.SetProviderConfig(ProviderDeepSeek, ProviderConfig{
					BaseURL:   DeepSeekBaseURL,
					ModelName: DefaultDeepSeekModel,
					APIKey:    dsKey,
				})
			}
			if geminiKey := strings.TrimSpace(os.Getenv("GEMINI_API_KEY")); geminiKey != "" {
				cfg.SetProviderConfig(ProviderGemini, ProviderConfig{
					BaseURL:   GeminiBaseURL,
					ModelName: DefaultGeminiModel,
					APIKey:    geminiKey,
				})
			} else if googleKey := strings.TrimSpace(os.Getenv("GOOGLE_API_KEY")); googleKey != "" {
				cfg.SetProviderConfig(ProviderGemini, ProviderConfig{
					BaseURL:   GeminiBaseURL,
					ModelName: DefaultGeminiModel,
					APIKey:    googleKey,
				})
			}

			// 预置 llamacpp
			cfg.SetProviderConfig(ProviderLlamaCpp, ProviderConfig{
				BaseURL:   DefaultLlamaCppBaseURL,
				ModelName: DefaultLlamaCppModel,
			})

			// 默认激活提供商选择
			if cfg.GetProviderConfig(ProviderDeepSeek).APIKey != "" {
				cfg.SwitchProvider(ProviderDeepSeek)
			} else if cfg.GetProviderConfig(ProviderGemini).APIKey != "" {
				cfg.SwitchProvider(ProviderGemini)
			} else {
				cfg.SwitchProvider(ProviderLlamaCpp)
			}

			return cfg, nil
		}
		return nil, err
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	if cfg.Providers == nil {
		cfg.Providers = make(map[string]ProviderConfig)
	}

	// 保证顶层当前配置已落入 providers
	if cfg.Provider != "" {
		pcfg := cfg.GetProviderConfig(cfg.Provider)
		if pcfg.APIKey == "" && cfg.APIKey != "" {
			pcfg.APIKey = cfg.APIKey
		}
		if pcfg.ModelName == "" && cfg.ModelName != "" {
			pcfg.ModelName = cfg.ModelName
		}
		if pcfg.BaseURL == "" && cfg.BaseURL != "" {
			pcfg.BaseURL = cfg.BaseURL
		}
		cfg.SetProviderConfig(cfg.Provider, pcfg)
	}

	// 环境变量补充
	if dsKey := strings.TrimSpace(os.Getenv("DEEPSEEK_API_KEY")); dsKey != "" {
		pcfg := cfg.GetProviderConfig(ProviderDeepSeek)
		if pcfg.APIKey == "" {
			pcfg.APIKey = dsKey
			if pcfg.ModelName == "" {
				pcfg.ModelName = DefaultDeepSeekModel
			}
			if pcfg.BaseURL == "" {
				pcfg.BaseURL = DeepSeekBaseURL
			}
			cfg.SetProviderConfig(ProviderDeepSeek, pcfg)
		}
	}
	if geminiKey := strings.TrimSpace(os.Getenv("GEMINI_API_KEY")); geminiKey != "" {
		pcfg := cfg.GetProviderConfig(ProviderGemini)
		if pcfg.APIKey == "" {
			pcfg.APIKey = geminiKey
			if pcfg.ModelName == "" {
				pcfg.ModelName = DefaultGeminiModel
			}
			if pcfg.BaseURL == "" {
				pcfg.BaseURL = GeminiBaseURL
			}
			cfg.SetProviderConfig(ProviderGemini, pcfg)
		}
	}

	// 确保当前激活项有效
	if cfg.Provider == "" {
		cfg.Provider = ProviderLlamaCpp
	}
	activePcfg := cfg.GetProviderConfig(cfg.Provider)
	if cfg.APIKey == "" && activePcfg.APIKey != "" {
		cfg.APIKey = activePcfg.APIKey
	}
	if cfg.ModelName == "" {
		if activePcfg.ModelName != "" {
			cfg.ModelName = activePcfg.ModelName
		} else {
			cfg.ModelName = GetDefaultModelForProvider(cfg.Provider)
		}
	}
	if cfg.BaseURL == "" {
		if activePcfg.BaseURL != "" {
			cfg.BaseURL = activePcfg.BaseURL
		} else {
			cfg.BaseURL = GetDefaultBaseURLForProvider(cfg.Provider)
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
	resolvedPath := ResolveConfigPath(path)

	dir := filepath.Dir(resolvedPath)
	if dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
	}

	// 确保当前选中的配置也同步记录在 providers map 中
	if cfg.Provider != "" {
		cfg.SetProviderConfig(cfg.Provider, ProviderConfig{
			BaseURL:   cfg.BaseURL,
			ModelName: cfg.ModelName,
			APIKey:    cfg.APIKey,
		})
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(resolvedPath, data, 0o600)
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
