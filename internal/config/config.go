// Package config 负责读取并校验 config.yaml 参数。
package config

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/spf13/viper"
)

const ConfigPath = "internal/config/config.yaml"

type Config struct {
	APP         APPConfig         `mapstructure:"app"`
	Log         LogConfig         `mapstructure:"log"`
	JWT         JWTConfig         `mapstructure:"jwt"`
	LLM         LLMConfig         `mapstructure:"llm"`
	Database    DatabaseConfig    `mapstructure:"database"`
	Chat        ChatConfig        `mapstructure:"chat"`
	Attachments AttachmentsConfig `mapstructure:"attachments"`
	Search      SearchConfig      `mapstructure:"search"`
}

type ChatConfig struct {
	ShellTimeout time.Duration `mapstructure:"shell_timeout"`
	MaxSteps     int           `mapstructure:"max_steps"`
	RunTimeout   time.Duration `mapstructure:"run_timeout"`
	Heartbeat    time.Duration `mapstructure:"heartbeat"`
}

type AttachmentsConfig struct {
	MaxBytes        int64 `mapstructure:"max_bytes"`
	MaxExtractChars int   `mapstructure:"max_extract_chars"`
	MaxPerMessage   int   `mapstructure:"max_per_message"`
}

type SearchConfig struct {
	Provider string `mapstructure:"provider"`
	APIKey   string `mapstructure:"api_key"`
	BaseURL  string `mapstructure:"base_url"`
}

type APPConfig struct {
	Name string `mapstructure:"name"`
	Env  string `mapstructure:"env"`
	Host string `mapstructure:"host"`
	Port string `mapstructure:"port"`
}

func (a APPConfig) IsProd() bool { return a.Env == "production" }

func (a APPConfig) Addr() string {
	host := strings.TrimSpace(a.Host)
	if host == "" {
		host = "0.0.0.0"
	}
	port := strings.TrimSpace(a.Port)
	if port == "" {
		port = "8080"
	}
	return host + ":" + port
}

type LogConfig struct {
	Dir       string `mapstructure:"dir"`
	Level     string `mapstructure:"level"`
	MaxSize   int    `mapstructure:"max_size"`
	MaxBackup int    `mapstructure:"max_backup"`
	Compress  bool   `mapstructure:"compress"`
}

type JWTConfig struct {
	Secret string        `mapstructure:"secret"`
	Issuer string        `mapstructure:"issuer"`
	Expire time.Duration `mapstructure:"expire"`
}

type LLMConfig struct {
	Provider      string         `mapstructure:"provider"`
	Model         string         `mapstructure:"model"`
	BaseURL       string         `mapstructure:"base_url"`
	APIKey        string         `mapstructure:"api_key"`
	ContextWindow int            `mapstructure:"context_window"`
	MaxToken      int            `mapstructure:"max_token"`
	Timeout       time.Duration  `mapstructure:"timeout"`
	ThinkingMode  string         `mapstructure:"thinking_mode"`
	ExtraFields   map[string]any `mapstructure:"extra_fields"`
}

type DatabaseConfig struct {
	MySQL MySQLConfig `mapstructure:"mysql"`
}

type MySQLConfig struct {
	Database        string        `mapstructure:"database"`
	Username        string        `mapstructure:"username"`
	Password        string        `mapstructure:"password"`
	DSN             string        `mapstructure:"dsn"`
	MaxIdleConns    int           `mapstructure:"max_idle_conns"`
	MaxOpenConns    int           `mapstructure:"max_open_conns"`
	ConnMaxLifetime time.Duration `mapstructure:"conn_max_lifetime"`
}

func (m MySQLConfig) BuildDSN() string {
	if strings.TrimSpace(m.DSN) != "" {
		return m.DSN
	}
	return fmt.Sprintf(
		"%s:%s@tcp(127.0.0.1:3306)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		m.Username, m.Password, m.Database,
	)
}

func Load() (*Config, error) {
	path := ConfigPath
	if p := strings.TrimSpace(os.Getenv("APP_CONFIG_PATH")); p != "" {
		path = p
	}

	rawContent, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("读取配置文件 %s 失败: %w", path, err)
	}

	content := stripYAMLComments(string(rawContent))
	if undefined := undefinedEnvKeys(content); len(undefined) > 0 {
		return nil, fmt.Errorf("配置引用了未定义的环境变量: %s", strings.Join(undefined, ", "))
	}

	v := viper.New()
	v.SetConfigType("yaml")
	if err := v.ReadConfig(strings.NewReader(os.ExpandEnv(content))); err != nil {
		return nil, fmt.Errorf("解析 YAML 配置失败: %w", err)
	}

	var c Config
	if err := v.Unmarshal(&c); err != nil {
		return nil, fmt.Errorf("反序列化配置到结构体失败: %w", err)
	}

	c.applyDefaults()
	if err := c.validate(); err != nil {
		return nil, err
	}
	return &c, nil
}

func undefinedEnvKeys(content string) []string {
	var undefined []string
	seen := make(map[string]struct{})
	rest := content
	for {
		start := strings.Index(rest, "${")
		if start < 0 {
			break
		}
		rest = rest[start+2:]
		end := strings.Index(rest, "}")
		if end < 0 {
			break
		}
		key := strings.TrimSpace(rest[:end])
		rest = rest[end+1:]
		if key == "" {
			continue
		}
		if _, ok := seen[key]; ok {
			continue
		}
		if _, exists := os.LookupEnv(key); !exists {
			seen[key] = struct{}{}
			undefined = append(undefined, key)
		}
	}
	return undefined
}

func stripYAMLComments(content string) string {
	lines := strings.Split(content, "\n")
	for i, line := range lines {
		if strings.HasPrefix(strings.TrimSpace(line), "#") {
			lines[i] = ""
			continue
		}
		if idx := strings.Index(line, " #"); idx >= 0 {
			lines[i] = line[:idx]
		}
	}
	return strings.Join(lines, "\n")
}

func (c *Config) applyDefaults() {
	ch := &c.Chat
	if ch.ShellTimeout <= 0 {
		ch.ShellTimeout = 120 * time.Second
	}
	if ch.MaxSteps <= 0 {
		ch.MaxSteps = 40
	}
	if ch.RunTimeout <= 0 {
		ch.RunTimeout = 600 * time.Second
	}
	if ch.Heartbeat <= 0 {
		ch.Heartbeat = 15 * time.Second
	}
	if c.LLM.ContextWindow == 0 {
		c.LLM.ContextWindow = 1000000
	}
	if c.LLM.MaxToken == 0 {
		c.LLM.MaxToken = 131072
	}

	if c.LLM.Timeout <= 0 {
		c.LLM.Timeout = 60 * time.Second
	}
	if mode := strings.ToLower(strings.TrimSpace(c.LLM.ThinkingMode)); mode == "" {
		c.LLM.ThinkingMode = "first_call_only"
	} else {
		c.LLM.ThinkingMode = mode
	}

	at := &c.Attachments
	if at.MaxBytes <= 0 {
		at.MaxBytes = 5 << 20
	}
	if at.MaxExtractChars <= 0 {
		at.MaxExtractChars = 12000
	}
	if at.MaxPerMessage <= 0 {
		at.MaxPerMessage = 3
	}
}

func (c *Config) validate() error {
	if strings.TrimSpace(c.APP.Port) == "" {
		return fmt.Errorf("配置项 app.port 不能为空")
	}
	if c.JWT.Expire < time.Minute {
		return fmt.Errorf("配置项 jwt.expire 至少 1m，当前 %v（请检查是否漏写单位，如 168h）", c.JWT.Expire)
	}
	if len(c.JWT.Secret) < 32 {
		return fmt.Errorf("配置项 jwt.secret 长度至少 32 字节，当前 %d", len(c.JWT.Secret))
	}
	if strings.TrimSpace(c.LLM.APIKey) != "" && strings.TrimSpace(c.LLM.Model) == "" {
		return fmt.Errorf("已配置 llm.api_key，但 llm.model 为空")
	}
	switch c.LLM.ThinkingMode {
	case "first_call_only", "always", "disabled", "off":
	default:
		return fmt.Errorf("配置项 llm.thinking_mode(%q) 无效，仅支持 first_call_only / always / disabled / off", c.LLM.ThinkingMode)
	}
	if c.LLM.ContextWindow <= 0 || c.LLM.MaxToken <= 0 {
		return fmt.Errorf("llm.context_window 和 llm.max_token 必须为正数")
	}
	return nil
}
