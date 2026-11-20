// Package config 负责读取 internal/config/config.yaml 中的参数。
//
// 加载顺序：gotenv 加载 .env → 读取 config.yaml → os.ExpandEnv 展开 ${ENV}
// → viper 解析 → Unmarshal 到结构体 → 业务级校验。
package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/viper"
)

// ConfigPath 是配置文件的默认路径，可通过 APP_CONFIG_PATH 覆盖。
const ConfigPath = "internal/platform/config/config.yaml"

// Config 是 config.yaml 的根对象
type Config struct {
	APP      APPConfig      `mapstructure:"app"`
	Log      LogConfig      `mapstructure:"log"`
	JWT      JWTConfig      `mapstructure:"jwt"`
	LLM      LLMConfig      `mapstructure:"llm"`
	Database DatabaseConfig `mapstructure:"database"`
	Chat     ChatConfig     `mapstructure:"chat"`
}

// ChatConfig 对应 config.yaml 中的 chat 段落，控制 ChatAgent 与 Harness 行为。
type ChatConfig struct {
	// WorkspaceDir 会话工作目录根路径，实际路径为 {WorkspaceDir}/{user_id}/{session_id}
	WorkspaceDir string `mapstructure:"workspace_dir"`
	// OffloadRoot 工具结果卸载根目录，与工作目录分开以保持会话目录干净
	OffloadRoot string `mapstructure:"offload_dir"`
	// SkillsDir 技能目录，只读挂载为 Agent 的 /skills
	SkillsDir string `mapstructure:"skills_dir"`
	// MaxSteps Agent 单轮最大迭代步数
	MaxSteps int `mapstructure:"max_steps"`
	// RunTimeout 单轮生成总超时
	RunTimeout time.Duration `mapstructure:"run_timeout"`
	// Heartbeat SSE 心跳间隔
	Heartbeat time.Duration `mapstructure:"heartbeat"`
	// HistoryMaxMessages 送入模型的历史消息条数上限
	HistoryMaxMessages int `mapstructure:"history_max_messages"`
	// HistoryBudgetTokens 历史消息的 token 预算
	HistoryBudgetTokens int `mapstructure:"history_budget_tokens"`
	// CompressTriggerTokens 触发上下文压缩的 token 阈值
	CompressTriggerTokens int `mapstructure:"compress_trigger_tokens"`
	// CompressTriggerMessages 触发上下文压缩的消息条数阈值
	CompressTriggerMessages int `mapstructure:"compress_trigger_messages"`
	// CompressSourceMaxChars 单次送入压缩的原文最大字符数
	CompressSourceMaxChars int `mapstructure:"compress_source_max_chars"`
	// KeepRecentTurns 压缩时保留原文的最近轮数
	KeepRecentTurns int `mapstructure:"keep_recent_turns"`
	// MemoryMinTurns 触发长期记忆提取的未提取 user 轮数阈值
	MemoryMinTurns int `mapstructure:"memory_min_turns"`
	// MemoryMinTokens 触发长期记忆提取的未提取 token 阈值
	MemoryMinTokens int `mapstructure:"memory_min_tokens"`
	// MemoryMaxChars 长期记忆文档最大字符数
	MemoryMaxChars int `mapstructure:"memory_max_chars"`
	// TitleWorkers 异步生成标题的 worker 数
	TitleWorkers int `mapstructure:"title_workers"`
	// TitleTimeout 单次标题生成的超时。标题是异步副作用，
	// 但要留足余量：慢模型（如 Spark）首包就要十几秒。
	TitleTimeout time.Duration `mapstructure:"title_timeout"`
}

// SessionDir 返回指定用户会话的工作目录。
func (c ChatConfig) SessionDir(userID, sessionID string) string {
	return filepath.Join(c.WorkspaceDir, userID, sessionID)
}

// OffloadDir 返回工具结果卸载目录，与工作目录分开以保持会话目录干净。
func (c ChatConfig) OffloadDir(userID, sessionID string) string {
	root := c.OffloadRoot
	if root == "" {
		root = filepath.Join("workspace", ".offload")
	}
	return filepath.Join(root, userID, sessionID)
}

// APPConfig 对应 config.yaml 中的 app 段落
type APPConfig struct {
	Name string `mapstructure:"name"`
	Env  string `mapstructure:"env"`
	Host string `mapstructure:"host"`
	Port string `mapstructure:"port"`
}

// IsProd 判断是否生产环境。
func (a APPConfig) IsProd() bool { return a.Env == "production" }

// Addr 返回 host:port，供 net.Listen 与日志使用。
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

// LogConfig 对应 config.yaml 中的 log 段落
type LogConfig struct {
	Dir       string `mapstructure:"dir"`
	Level     string `mapstructure:"level"`
	MaxSize   int    `mapstructure:"max_size"`
	MaxBackup int    `mapstructure:"max_backup"`
	Compress  bool   `mapstructure:"compress"`
}

// JWTConfig 对应 config.yaml 中的 jwt 段落
type JWTConfig struct {
	Secret string `mapstructure:"secret"`
	Issuer string `mapstructure:"issuer"`
	// Expire 必须带单位（如 168h / 30m）。纯数字会被 viper 解析成纳秒，
	// 导致 token 一签发即过期——这个坑在 validate 里显式拦掉。
	Expire time.Duration `mapstructure:"expire"`
}

// LLMConfig 对应 config.yaml 中的 llm 段落
type LLMConfig struct {
	Provider    string         `mapstructure:"provider"`
	Model       string         `mapstructure:"model"`
	BaseURL     string         `mapstructure:"base_url"`
	APIKey      string         `mapstructure:"api_key"`
	MaxToken    int            `mapstructure:"max_token"`
	Timeout     time.Duration  `mapstructure:"timeout"`
	ExtraFields map[string]any `mapstructure:"extra_fields"`
}

// DatabaseConfig 对应 config.yaml 中的 database 段落
type DatabaseConfig struct {
	MySQL MySQLConfig `mapstructure:"mysql"`
	Redis RedisConfig `mapstructure:"redis"`
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

// BuildDSN 在 dsn 留空时按字段拼装，避免两处配置不一致。
// DSN 显式配置时以它为准（docker / CI 常直接注入整串）。
func (m MySQLConfig) BuildDSN() string {
	if strings.TrimSpace(m.DSN) != "" {
		return m.DSN
	}
	return fmt.Sprintf(
		"%s:%s@tcp(127.0.0.1:3306)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		m.Username, m.Password, m.Database,
	)
}

type RedisConfig struct {
	Addr     string `mapstructure:"addr"`
	Password string `mapstructure:"password"`
	DB       int    `mapstructure:"db"`
	PoolSize int    `mapstructure:"pool_size"`
}

var cfg *Config

// Load 读取并解析配置文件，成功后可通过 Get 获取全局实例。
func Load() (*Config, error) {
	path := ConfigPath
	if p := strings.TrimSpace(os.Getenv("APP_CONFIG_PATH")); p != "" {
		path = p
	}

	// 1. 读取原始配置文件
	rawContent, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("读取配置文件 %s 失败: %w", path, err)
	}

	// 2. 展开配置文件中的 ${ENV} 环境变量。
	// os.ExpandEnv 会把未设置的变量静默替换成空串，这里先把「未定义」和
	// 「显式留空」区分开：未定义多半是配置漏填，应当启动失败并报出变量名；
	// 显式留空（如本机 Redis 无密码）是合法场景，不能拦。
	content := stripYAMLComments(string(rawContent))
	if undefined := undefinedEnvKeys(content); len(undefined) > 0 {
		return nil, fmt.Errorf("配置引用了未定义的环境变量: %s", strings.Join(undefined, ", "))
	}

	v := viper.New()
	v.SetConfigType("yaml")
	if err := v.ReadConfig(strings.NewReader(os.ExpandEnv(content))); err != nil {
		return nil, fmt.Errorf("解析 YAML 配置失败: %w", err)
	}

	// 3. 反序列化到结构体。
	// viper 内置 StringToTimeDuration Hook，会把 "120s" / "1h" 转成 time.Duration。
	var c Config
	if err := v.Unmarshal(&c); err != nil {
		return nil, fmt.Errorf("反序列化配置到结构体失败: %w", err)
	}

	c.applyDefaults()

	if err := c.validate(); err != nil {
		return nil, err
	}

	cfg = &c
	return cfg, nil
}

// Get 获取全局配置实例，需先调用 Load。
func Get() *Config {
	return cfg
}

// undefinedEnvKeys 找出文本中形如 ${KEY}、但当前环境中完全没有定义的变量名。
// 注意：环境变量存在但值为空串属于「显式留空」，不算未定义。
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

// stripYAMLComments 去掉以 # 开头的注释内容。
// 注释里可能写着 ${ENV_KEY} 这类示例，不剔除会误判为缺失变量。
// 只处理行首注释与行尾 " #" 的简单情形，足以覆盖本项目配置。
func stripYAMLComments(content string) string {
	lines := strings.Split(content, "\n")
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "#") {
			lines[i] = ""
			continue
		}
		// 行尾注释：只在 # 前有空格时截断，避免误伤值里的 # 字符。
		if idx := strings.Index(line, " #"); idx >= 0 {
			lines[i] = line[:idx]
		}
	}
	return strings.Join(lines, "\n")
}

// applyDefaults 为 chat 段填充缺省值。
// 这些项即使配置文件漏写也应有合理默认，避免除零或空路径。
func (c *Config) applyDefaults() {
	ch := &c.Chat

	if strings.TrimSpace(ch.WorkspaceDir) == "" {
		ch.WorkspaceDir = "workspace/chat"
	}
	if strings.TrimSpace(ch.OffloadRoot) == "" {
		ch.OffloadRoot = "workspace/.offload"
	}
	if strings.TrimSpace(ch.SkillsDir) == "" {
		ch.SkillsDir = "skills"
	}
	if ch.MaxSteps <= 0 {
		ch.MaxSteps = 8
	}
	if ch.RunTimeout <= 0 {
		ch.RunTimeout = 600 * time.Second
	}
	if ch.Heartbeat <= 0 {
		ch.Heartbeat = 15 * time.Second
	}
	if ch.HistoryMaxMessages <= 0 {
		ch.HistoryMaxMessages = 40
	}
	if ch.HistoryBudgetTokens <= 0 {
		ch.HistoryBudgetTokens = 12000
	}
	if ch.CompressTriggerTokens <= 0 {
		ch.CompressTriggerTokens = 6000
	}
	if ch.CompressTriggerMessages <= 0 {
		ch.CompressTriggerMessages = 16
	}
	if ch.CompressSourceMaxChars <= 0 {
		ch.CompressSourceMaxChars = 8000
	}
	if ch.KeepRecentTurns <= 0 {
		ch.KeepRecentTurns = 2
	}
	if ch.MemoryMinTurns <= 0 {
		ch.MemoryMinTurns = 4
	}
	if ch.MemoryMinTokens <= 0 {
		ch.MemoryMinTokens = 4000
	}
	if ch.MemoryMaxChars <= 0 {
		ch.MemoryMaxChars = 2000
	}
	if ch.TitleWorkers <= 0 {
		ch.TitleWorkers = 4
	}
	if ch.TitleTimeout <= 0 {
		ch.TitleTimeout = 120 * time.Second
	}
}

// validate 做启动期的业务校验：能在这里发现的问题，不要留到运行时才暴露。
func (c *Config) validate() error {
	if strings.TrimSpace(c.APP.Port) == "" {
		return fmt.Errorf("配置项 app.port 不能为空")
	}

	// 低于 1 分钟基本等于「签发即过期」，几乎只可能来自漏写单位。
	if c.JWT.Expire < time.Minute {
		return fmt.Errorf("配置项 jwt.expire 至少 1m，当前 %v（请检查是否漏写单位，如 168h）", c.JWT.Expire)
	}

	// JWT 密钥过短会让 HS256 签名轻易被暴力破解，生产环境必须足够长。
	if len(c.JWT.Secret) < 32 {
		return fmt.Errorf("配置项 jwt.secret 长度至少 32 字节，当前 %d", len(c.JWT.Secret))
	}

	// LLM 允许留空（不启用 AI 能力），但填了 api_key 就必须有 model。
	if strings.TrimSpace(c.LLM.APIKey) != "" && strings.TrimSpace(c.LLM.Model) == "" {
		return fmt.Errorf("已配置 llm.api_key，但 llm.model 为空")
	}

	// 两个超时的关系必须自洽：单次模型调用超时若短于整轮超时，
	// 长回答会在流式传输中途被 HTTP 客户端掐断（实测 120s 对「详细讲解」
	// 明显不够，表现为整轮 cancelled 且 prompt_tokens 为空）。
	// 这类问题排查成本高，直接在启动期拦下。
	if c.LLM.Timeout > 0 && c.Chat.RunTimeout > 0 && c.LLM.Timeout < c.Chat.RunTimeout/2 {
		return fmt.Errorf(
			"llm.timeout(%s) 过小：应至少为 chat.run_timeout(%s) 的一半，"+
				"否则长回答会被单次调用超时截断",
			c.LLM.Timeout, c.Chat.RunTimeout,
		)
	}

	return nil
}
