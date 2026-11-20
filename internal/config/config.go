// Package config 负责读取 config.yaml 中的参数。
//
// 加载顺序：gotenv 加载 .env → 读取 config.yaml → os.ExpandEnv 展开 ${ENV}
// → viper 解析 → Unmarshal 到结构体 → 业务级校验。
package config

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/spf13/viper"
)

// ConfigPath 是配置文件的默认路径，可通过 APP_CONFIG_PATH 覆盖。
const ConfigPath = "internal/config/config.yaml"

// Config 是 config.yaml 的根对象
type Config struct {
	APP         APPConfig         `mapstructure:"app"`
	Log         LogConfig         `mapstructure:"log"`
	JWT         JWTConfig         `mapstructure:"jwt"`
	LLM         LLMConfig         `mapstructure:"llm"`
	Database    DatabaseConfig    `mapstructure:"database"`
	Chat        ChatConfig        `mapstructure:"chat"`
	Attachments AttachmentsConfig `mapstructure:"attachments"`
	Artifacts   ArtifactsConfig   `mapstructure:"artifacts"`
	Search      SearchConfig      `mapstructure:"search"`
}

// ChatConfig 对应 config.yaml 中的 chat 段落，控制 Tutor Harness 与 Agent 行为。
type ChatConfig struct {
	// WorkspaceDir 会话工作目录根路径，实际路径为 {WorkspaceDir}/{user_id}/{conversation_id}
	WorkspaceDir string `mapstructure:"workspace_dir"`
	// OffloadRoot 工具结果卸载根目录，与工作目录分开以保持会话目录干净
	OffloadRoot string `mapstructure:"offload_dir"`
	// SkillsDir 技能目录，只读挂载为 Agent 的 /skills
	SkillsDir string `mapstructure:"skills_dir"`
	// MaxSteps Agent 单轮最大 ReAct 迭代步数
	MaxSteps int `mapstructure:"max_steps"`
	// RunTimeout 单轮生成总超时
	RunTimeout time.Duration `mapstructure:"run_timeout"`
	// Heartbeat SSE 心跳间隔
	Heartbeat time.Duration `mapstructure:"heartbeat"`
	// SummaryTriggerTokens 触发官方 Summarization Middleware 的 token 阈值
	SummaryTriggerTokens int `mapstructure:"summary_trigger_tokens"`
	// SummaryTriggerMessages 触发官方 Summarization Middleware 的消息条数阈值
	SummaryTriggerMessages int `mapstructure:"summary_trigger_messages"`
	// TitleWorkers 异步生成标题的 worker 数
	TitleWorkers int `mapstructure:"title_workers"`
	// TitleTimeout 单次标题生成超时
	TitleTimeout time.Duration `mapstructure:"title_timeout"`
}

// AttachmentsConfig 控制附件上传与文本提取。
type AttachmentsConfig struct {
	Dir             string `mapstructure:"dir"`
	MaxBytes        int64  `mapstructure:"max_bytes"`
	MaxExtractChars int    `mapstructure:"max_extract_chars"`
}

// ArtifactsConfig 控制 Artifact 存储与异步生成任务。
type ArtifactsConfig struct {
	Dir         string        `mapstructure:"dir"`
	JobWorkers  int           `mapstructure:"job_workers"`
	JobTimeout  time.Duration `mapstructure:"job_timeout"`
	FFmpegPath  string        `mapstructure:"ffmpeg_path"`
	FontPath    string        `mapstructure:"font_path"`
	VideoWidth  int           `mapstructure:"video_width"`
	VideoHeight int           `mapstructure:"video_height"`
	VideoFPS    int           `mapstructure:"video_fps"`
}

// SearchConfig 是可选联网搜索能力。api_key 为空时不注册搜索工具。
type SearchConfig struct {
	Provider string `mapstructure:"provider"`
	APIKey   string `mapstructure:"api_key"`
	BaseURL  string `mapstructure:"base_url"`
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
	// Vision 表示当前模型是否支持图片原生输入。
	// 为 false 时不会把图片内联进消息，而是提示模型改用文本途径。
	Vision bool `mapstructure:"vision"`
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
	if ch.SummaryTriggerTokens <= 0 {
		ch.SummaryTriggerTokens = 60000
	}
	if ch.SummaryTriggerMessages <= 0 {
		ch.SummaryTriggerMessages = 40
	}
	if ch.TitleWorkers <= 0 {
		ch.TitleWorkers = 4
	}
	if ch.TitleTimeout <= 0 {
		ch.TitleTimeout = 120 * time.Second
	}

	at := &c.Attachments
	if strings.TrimSpace(at.Dir) == "" {
		at.Dir = "workspace/attachments"
	}
	if at.MaxBytes <= 0 {
		at.MaxBytes = 32 << 20
	}
	if at.MaxExtractChars <= 0 {
		at.MaxExtractChars = 20000
	}

	ar := &c.Artifacts
	if strings.TrimSpace(ar.Dir) == "" {
		ar.Dir = "workspace/artifacts"
	}
	if ar.JobWorkers <= 0 {
		ar.JobWorkers = 2
	}
	if ar.JobTimeout <= 0 {
		ar.JobTimeout = 10 * time.Minute
	}
	if strings.TrimSpace(ar.FFmpegPath) == "" {
		ar.FFmpegPath = "ffmpeg"
	}
	if ar.VideoWidth <= 0 {
		ar.VideoWidth = 1280
	}
	if ar.VideoHeight <= 0 {
		ar.VideoHeight = 720
	}
	if ar.VideoFPS <= 0 {
		ar.VideoFPS = 30
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
