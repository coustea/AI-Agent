package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"

	"my-agent/internal/protocol"
)

// Version 当前软件发布版本号（可通过编译期 -ldflags "-X my-agent/internal/config.Version=..." 覆盖）
var Version = "v1.2.0"

// Config 保存大模型标准统一配置（基于标准 OpenAI 兼容三要素驱动）
type Config struct {
	BaseURL   string `json:"base_url"`          // 服务端点地址 (如 https://api.openai.com/v1, http://127.0.0.1:11434)
	APIKey    string `json:"api_key,omitempty"` // API 密钥 (本地服务可空)
	ModelName string `json:"model_name"`        // 默认模型名称 (如 gpt-4o, deepseek-chat, qwen2.5:7b)
}

// GlobalConfigDir 返回用户级全局配置目录 (~/.tide)
func GlobalConfigDir() string {
	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		return "."
	}
	return filepath.Join(home, ".tide")
}

// GlobalConfigPath 返回用户级全局配置文件路径 (~/.tide/config.json)
func GlobalConfigPath() string {
	return filepath.Join(GlobalConfigDir(), "config.json")
}

// ResolveConfigPath 解析生效的配置文件路径：
// 1. 若指定了非空 path，优先使用指定的 path；
// 2. 若当前工作目录下存在 config.json，优先使用当前项目目录的本地配置；
// 3. 否则默认使用用户主目录下的全局配置 (~/.tide/config.json)。
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

// Clone 返回当前配置对象的深拷贝副本
func (c *Config) Clone() *Config {
	if c == nil {
		return nil
	}
	cp := *c
	return &cp
}

// IsLocalURL 判定端点是否属于本地免密钥服务 (127.0.0.1 / localhost / ::1)
func IsLocalURL(u string) bool {
	u = strings.ToLower(strings.TrimSpace(u))
	return strings.Contains(u, "127.0.0.1") || strings.Contains(u, "localhost") || strings.Contains(u, "::1")
}

// firstEnv 返回第一个非空的环境变量值
func firstEnv(keys ...string) string {
	for _, k := range keys {
		if v := strings.TrimSpace(os.Getenv(k)); v != "" {
			return v
		}
	}
	return ""
}

// DefaultConfig 构建全新的默认配置，自动补全环境变量
func DefaultConfig() *Config {
	baseURL := firstEnv("OPENAI_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.openai.com/v1"
	}

	apiKey := firstEnv("OPENAI_API_KEY")

	modelName := firstEnv("OPENAI_MODEL")
	if modelName == "" {
		modelName = "gpt-4o"
	}

	return &Config{
		BaseURL:   baseURL,
		APIKey:    apiKey,
		ModelName: modelName,
	}
}

// LoadConfig 从指定 JSON 文件加载配置，支持自动发现与环境变量兜底补齐
func LoadConfig(path string) (*Config, error) {
	resolvedPath := ResolveConfigPath(path)

	data, err := os.ReadFile(resolvedPath)
	if err != nil {
		if os.IsNotExist(err) {
			return DefaultConfig(), nil
		}
		return nil, err
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	// 补全环境变量与默认值
	if cfg.BaseURL == "" {
		if v := firstEnv("OPENAI_BASE_URL"); v != "" {
			cfg.BaseURL = v
		} else {
			cfg.BaseURL = "https://api.openai.com/v1"
		}
	}
	if cfg.APIKey == "" {
		cfg.APIKey = firstEnv("OPENAI_API_KEY")
	}
	if cfg.ModelName == "" {
		if v := firstEnv("OPENAI_MODEL"); v != "" {
			cfg.ModelName = v
		} else {
			cfg.ModelName = "gpt-4o"
		}
	}

	return &cfg, nil
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

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(resolvedPath, data, 0o600)
}

// ToView 将当前配置映射为面向前端只读呈现的纯数据 ConfigView 契约
func (c *Config) ToView() protocol.ConfigView {
	if c == nil {
		return protocol.ConfigView{}
	}
	return protocol.ConfigView{
		BaseURL:   c.BaseURL,
		ModelName: c.ModelName,
		HasAPIKey: c.APIKey != "" || IsLocalURL(c.BaseURL),
	}
}
