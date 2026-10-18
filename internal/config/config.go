package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"

	"my-agent/internal/protocol"
)

// Provider 定义支持的模型厂商
type Provider string

const (
	ProviderLlamaCpp Provider = "llamacpp"
	ProviderDeepSeek Provider = "deepseek"
	ProviderGemini   Provider = "gemini"
	ProviderSpark    Provider = "spark"
)

// 默认模型与服务端点推荐
const (
	// llama.cpp 本地 HTTP 服务默认配置
	DefaultLlamaCppBaseURL = "http://127.0.0.1:8080"
	DefaultLlamaCppModel   = "local-model"

	// DeepSeek 官方最新模型规范 (V4 系列与 R1 推理)
	DefaultDeepSeekModel  = "deepseek-flash"
	DeepSeekProModel      = "deepseek-v4-pro"
	DeepSeekReasonerModel = "deepseek-reasoner"
	DeepSeekBaseURL       = "https://api.deepseek.com"

	// Google Gemini 官方最新模型规范 (兼容 OpenAI 协议端点)
	DefaultGeminiModel = "gemini-2.5-flash"
	GeminiProModel     = "gemini-2.5-pro"
	GeminiBaseURL      = "https://generativelanguage.googleapis.com/v1beta/openai"

	// 讯飞星辰 MaaS 官方最新模型规范 (https://maas.xfyun.cn/modelSquare)
	SparkX25Model       = "spark-x2.5"    // 官方主力免费体验模型 (256K 超长上下文，带深度推理)
	SparkX254BModel     = "spark-x2.5-4b" // 端侧 4B 免费开源模型 (原生 1M 超长上下文，0元/tokens)
	DefaultSparkModel   = SparkX25Model   // 默认主力模型 spark-x2.5
	DefaultSparkBaseURL = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
)

// DefaultSparkAPIKey 系统内置免费星火 API Key。
// 推荐在编译期通过 -ldflags "-X my-agent/internal/config.DefaultSparkAPIKey=..." 动态注入，
// 避免明文泄露到 Git 仓库中。
var DefaultSparkAPIKey = ""

// Version 当前软件发布版本号（可通过编译期 -ldflags "-X my-agent/internal/config.Version=..." 覆盖）
var Version = "v1.0.0"

// providerMeta 描述一个模型厂商的静态元数据，是全部厂商相关映射的单一来源。
type providerMeta struct {
	ID                string
	Aliases           []string
	DefaultBaseURL    string
	DefaultModel      string
	RecommendedModels []string
	DisplayName       string
	Description       string
	IsLocal           bool
	ModelPrefixes     []string
	ModelSubstrings   []string
}

// providerRegistry 是全部厂商元数据的唯一注册表，按展示顺序排列。
var providerRegistry = []providerMeta{
	{
		ID:                "llamacpp",
		Aliases:           []string{"llama", "local"},
		DefaultBaseURL:    DefaultLlamaCppBaseURL,
		DefaultModel:      DefaultLlamaCppModel,
		RecommendedModels: []string{DefaultLlamaCppModel, "qwen2.5-coder-7b"},
		DisplayName:       "llama.cpp",
		Description:       "本地 HTTP 服务 (127.0.0.1:8080)",
		IsLocal:           true,
		ModelSubstrings:   []string{"llama", "local", "qwen"},
	},
	{
		ID:                "deepseek",
		Aliases:           []string{"ds"},
		DefaultBaseURL:    DeepSeekBaseURL,
		DefaultModel:      DefaultDeepSeekModel,
		RecommendedModels: []string{DefaultDeepSeekModel, DeepSeekProModel, DeepSeekReasonerModel},
		DisplayName:       "DeepSeek",
		Description:       "官方最新 - 支持 V4 系列与 R1 深度推理",
		ModelPrefixes:     []string{"deepseek"},
	},
	{
		ID:                "gemini",
		Aliases:           []string{"google"},
		DefaultBaseURL:    GeminiBaseURL,
		DefaultModel:      DefaultGeminiModel,
		RecommendedModels: []string{DefaultGeminiModel, GeminiProModel},
		DisplayName:       "Google Gemini",
		Description:       "官方最新 - 推荐 Flash 极速响应 / Pro 深度代码",
		ModelPrefixes:     []string{"gemini"},
	},
	{
		ID:             "spark",
		Aliases:        []string{"maas", "xfyun"},
		DefaultBaseURL: DefaultSparkBaseURL,
		DefaultModel:   DefaultSparkModel,
		RecommendedModels: []string{
			SparkX25Model,   // spark-x2.5 (官方主力免费体验模型，256K 超长上下文)
			SparkX254BModel, // spark-x2.5-4b (端侧 4B 免费开源模型，1M 超长上下文，0元)
		},
		DisplayName:   "讯飞星辰 MaaS",
		Description:   "官方免费模型 - 默认 spark-x2.5 (主力) / spark-x2.5-4b (1M上下文)",
		ModelPrefixes: []string{"spark"},
	},
}

// canonicalProvider 返回厂商的规范 ID；未知输入返回其小写形式。
func canonicalProvider(p Provider) string {
	key := strings.ToLower(string(p))
	for _, pm := range providerRegistry {
		if pm.ID == key {
			return pm.ID
		}
		for _, a := range pm.Aliases {
			if a == key {
				return pm.ID
			}
		}
	}
	return key
}

// lookupProvider 返回厂商元数据；未知厂商返回 nil。
func lookupProvider(p Provider) *providerMeta {
	key := canonicalProvider(p)
	for i := range providerRegistry {
		if providerRegistry[i].ID == key {
			return &providerRegistry[i]
		}
	}
	return nil
}

// ProviderIDs 返回按展示顺序排列的全部厂商规范 ID。
func ProviderIDs() []string {
	ids := make([]string, 0, len(providerRegistry))
	for _, pm := range providerRegistry {
		ids = append(ids, pm.ID)
	}
	return ids
}

// ProviderID 返回厂商的规范 ID（别名归一化）。
func ProviderID(p Provider) string {
	return canonicalProvider(p)
}

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

// ProviderFor 获取指定厂商已保存的配置
func (c Config) ProviderFor(p Provider) ProviderConfig {
	if c.Providers == nil {
		return ProviderConfig{}
	}
	return c.Providers[canonicalProvider(p)]
}

// SetProviderConfig 记录并更新指定厂商的专属配置
func (c *Config) SetProviderConfig(p Provider, pcfg ProviderConfig) {
	if c.Providers == nil {
		c.Providers = make(map[string]ProviderConfig)
	}
	c.Providers[canonicalProvider(p)] = pcfg
}

// SwitchProvider 切换当前激活的厂商，并自动载入该厂商已保存的配置历史
func (c *Config) SwitchProvider(p Provider) {
	c.Provider = p
	pcfg := c.ProviderFor(p)

	if pcfg.BaseURL != "" {
		c.BaseURL = pcfg.BaseURL
	} else {
		c.BaseURL = DefaultBaseURL(p)
	}

	if pcfg.ModelName != "" {
		c.ModelName = NormalizeModelName(p, pcfg.ModelName)
	} else {
		c.ModelName = DefaultModel(p)
	}

	c.APIKey = pcfg.APIKey
}

// envFallback 描述一个厂商的环境变量密钥来源与默认端点/模型。
type envFallback struct {
	provider Provider
	envKeys  []string
	baseURL  string
	model    string
}

// envFallbacks 是环境变量补全的唯一来源。
var envFallbacks = []envFallback{
	{ProviderDeepSeek, []string{"DEEPSEEK_API_KEY"}, DeepSeekBaseURL, DefaultDeepSeekModel},
	{ProviderGemini, []string{"GEMINI_API_KEY", "GOOGLE_API_KEY"}, GeminiBaseURL, DefaultGeminiModel},
	{ProviderSpark, []string{"SPARK_API_KEY", "MAAS_API_KEY"}, DefaultSparkBaseURL, DefaultSparkModel},
}

// applyEnvFallbacks 使用环境变量补齐缺失的厂商密钥与默认端点/模型。
func applyEnvFallbacks(cfg *Config) {
	for _, fb := range envFallbacks {
		pcfg := cfg.ProviderFor(fb.provider)
		if pcfg.APIKey != "" {
			continue
		}
		key := firstEnv(fb.envKeys...)
		if key == "" {
			continue
		}
		pcfg.APIKey = key
		if pcfg.BaseURL == "" {
			pcfg.BaseURL = fb.baseURL
		}
		if pcfg.ModelName == "" {
			pcfg.ModelName = fb.model
		}
		cfg.SetProviderConfig(fb.provider, pcfg)
	}
}

// firstEnv 返回第一个非空的环境变量值。
func firstEnv(keys ...string) string {
	for _, k := range keys {
		if v := strings.TrimSpace(os.Getenv(k)); v != "" {
			return v
		}
	}
	return ""
}

// DefaultConfig 构建一份全新的默认配置（含环境变量密钥自动补全与 llamacpp 预置），
// 作为配置文件缺失或损坏时的安全回退。
func DefaultConfig() *Config {
	cfg := &Config{
		Providers: make(map[string]ProviderConfig),
	}

	// 收集环境变量中的密钥
	applyEnvFallbacks(cfg)

	// 预置 llamacpp
	cfg.SetProviderConfig(ProviderLlamaCpp, ProviderConfig{
		BaseURL:   DefaultLlamaCppBaseURL,
		ModelName: DefaultLlamaCppModel,
	})

	// 预置 spark 默认端点与默认免费模型 (优先使用用户环境变量/配置；若无则回退到编译期注入的 DefaultSparkAPIKey)
	pcfgSpark := cfg.ProviderFor(ProviderSpark)
	if pcfgSpark.BaseURL == "" {
		pcfgSpark.BaseURL = DefaultSparkBaseURL
	}
	if pcfgSpark.ModelName == "" {
		pcfgSpark.ModelName = DefaultSparkModel
	}
	if pcfgSpark.APIKey == "" && strings.TrimSpace(DefaultSparkAPIKey) != "" {
		pcfgSpark.APIKey = strings.TrimSpace(DefaultSparkAPIKey)
	}
	cfg.SetProviderConfig(ProviderSpark, pcfgSpark)

	// 默认激活提供商选择：
	// 1. 若外部环境变量显式配置了 DeepSeek 或 Gemini，优先激活对应厂商；
	// 2. 否则系统默认激活官方免费模型 (Spark spark-2.5)
	if cfg.ProviderFor(ProviderDeepSeek).APIKey != "" {
		cfg.SwitchProvider(ProviderDeepSeek)
	} else if cfg.ProviderFor(ProviderGemini).APIKey != "" {
		cfg.SwitchProvider(ProviderGemini)
	} else {
		cfg.SwitchProvider(ProviderSpark)
	}

	return cfg
}

// LoadConfig 从指定 JSON 文件加载配置，支持全局/本地发现与环境变量自动补全
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

	if cfg.Providers == nil {
		cfg.Providers = make(map[string]ProviderConfig)
	}

	// 保证顶层当前配置已落入 providers
	if cfg.Provider != "" {
		pcfg := cfg.ProviderFor(cfg.Provider)
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
	applyEnvFallbacks(&cfg)

	// 确保当前激活项有效
	if cfg.Provider == "" {
		cfg.Provider = ProviderLlamaCpp
	}
	activePcfg := cfg.ProviderFor(cfg.Provider)
	if cfg.APIKey == "" && activePcfg.APIKey != "" {
		cfg.APIKey = activePcfg.APIKey
	}
	if cfg.ModelName == "" {
		if activePcfg.ModelName != "" {
			cfg.ModelName = activePcfg.ModelName
		} else {
			cfg.ModelName = DefaultModel(cfg.Provider)
		}
	}
	cfg.ModelName = NormalizeModelName(cfg.Provider, cfg.ModelName)
	for pName, pcfg := range cfg.Providers {
		pcfg.ModelName = NormalizeModelName(Provider(pName), pcfg.ModelName)
		cfg.Providers[pName] = pcfg
	}

	if cfg.BaseURL == "" {
		if activePcfg.BaseURL != "" {
			cfg.BaseURL = activePcfg.BaseURL
		} else {
			cfg.BaseURL = DefaultBaseURL(cfg.Provider)
		}
	}

	// 远程云端服务缺密钥不再视为加载失败：未就绪状态由上层视图（ConfigView.HasAPIKey）表达，
	// 待 /model 配置向导补齐密钥后由内核热装网关。
	return &cfg, nil
}

// IsLocalProvider 判断是否为无需鉴权的本地服务提供商
func IsLocalProvider(p Provider) bool {
	if pm := lookupProvider(p); pm != nil {
		return pm.IsLocal
	}
	return false
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

// metaOrDefault 返回厂商元数据；未知厂商回退到本地 llamacpp。
func metaOrDefault(p Provider) *providerMeta {
	if pm := lookupProvider(p); pm != nil {
		return pm
	}
	return lookupProvider(ProviderLlamaCpp)
}

// DefaultModel 根据厂商返回最新默认模型名称
func DefaultModel(p Provider) string {
	return metaOrDefault(p).DefaultModel
}

// DefaultBaseURL 根据厂商返回默认服务端点
func DefaultBaseURL(p Provider) string {
	return metaOrDefault(p).DefaultBaseURL
}

// RecommendedModels 返回指定厂商官方推荐的高频常用模型列表
func RecommendedModels(p Provider) []string {
	return metaOrDefault(p).RecommendedModels
}

// ProviderDisplayName 返回厂商的友好展示名称
func ProviderDisplayName(p Provider) string {
	return metaOrDefault(p).DisplayName
}

// ProviderDescription 返回厂商的能力特征说明
func ProviderDescription(p Provider) string {
	return metaOrDefault(p).Description
}

// InferProviderFromModel 根据模型名称前缀或特征智能识别所属厂商
func InferProviderFromModel(model string) Provider {
	m := strings.ToLower(strings.TrimSpace(model))
	for _, pm := range providerRegistry {
		for _, prefix := range pm.ModelPrefixes {
			if strings.HasPrefix(m, prefix) {
				return Provider(pm.ID)
			}
		}
		for _, sub := range pm.ModelSubstrings {
			if strings.Contains(m, sub) {
				return Provider(pm.ID)
			}
		}
	}
	return ""
}

// NormalizeModelName 归一化各厂商的模型名称，自动修复星火平台缺少 x 前缀的笔误（如 spark-2.5 修正为 spark-x2.5）
func NormalizeModelName(p Provider, model string) string {
	m := strings.TrimSpace(model)
	if m == "" {
		return DefaultModel(p)
	}
	canon := canonicalProvider(p)
	if canon == "spark" {
		low := strings.ToLower(m)
		switch low {
		case "spark-2.5", "2.5":
			return SparkX25Model
		case "spark-2.5-4b", "2.5-4b", "spark-4b", "4b":
			return SparkX254BModel
		}
	}
	return m
}

// ToView 将当前配置映射为面向前端只读呈现的纯数据 ConfigView 契约
func (c *Config) ToView() protocol.ConfigView {
	available := ProviderIDs()

	cv := protocol.ConfigView{
		AvailableProviders: available,
	}
	if c != nil {
		cv.Provider = string(c.Provider)
		cv.ModelName = c.ModelName
		cv.HasAPIKey = c.APIKey != "" || IsLocalProvider(c.Provider)
	}

	providers := make([]protocol.ProviderInfo, 0, len(available))
	for _, pStr := range available {
		p := Provider(pStr)
		info := protocol.ProviderInfo{
			ID:                pStr,
			Name:              ProviderDisplayName(p),
			Description:       ProviderDescription(p),
			IsLocal:           IsLocalProvider(p),
			RecommendedModels: RecommendedModels(p),
		}

		if c != nil {
			pcfg := c.ProviderFor(p)
			if pcfg.ModelName != "" {
				info.CurrentModel = pcfg.ModelName
			} else {
				info.CurrentModel = DefaultModel(p)
			}

			if info.IsLocal {
				info.IsConfigured = true
			} else if pcfg.APIKey != "" {
				info.IsConfigured = true
			} else if c.Provider == p && c.APIKey != "" {
				info.IsConfigured = true
			}
		} else {
			info.CurrentModel = DefaultModel(p)
			info.IsConfigured = info.IsLocal
		}

		providers = append(providers, info)
	}
	cv.Providers = providers
	return cv
}
