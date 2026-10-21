package config

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"my-agent/pkg/llm"
)

// providerMeta 保存厂商的展示层元数据；
// 网络事实（端点、chat 路径、默认模型、鉴权、Local）由 pkg/llm.Spec 提供。
type providerMeta struct {
	ID                llm.Provider
	DisplayName       string
	Description       string
	Aliases           []string
	RecommendedModels []string
	ModelPrefixes     []string
	ModelSubstrings   []string
	EnvKeys           []string
}

// providerMetas 的顺序即前端展示顺序。
var providerMetas = []providerMeta{
	{
		ID:                llm.ProviderLlamaCpp,
		DisplayName:       "llama.cpp",
		Description:       "本地 HTTP 服务 (127.0.0.1:8080)",
		Aliases:           []string{"llama", "local"},
		RecommendedModels: []string{"local-model", "qwen2.5-coder-7b"},
		ModelSubstrings:   []string{"llama", "local", "qwen"},
	},
	{
		ID:                llm.ProviderDeepSeek,
		DisplayName:       "DeepSeek",
		Description:       "官方最新 - 支持 V4 系列与 R1 深度推理",
		Aliases:           []string{"ds"},
		RecommendedModels: []string{"deepseek-flash", "deepseek-v4-pro", "deepseek-reasoner"},
		ModelPrefixes:     []string{"deepseek"},
		EnvKeys:           []string{"DEEPSEEK_API_KEY"},
	},
	{
		ID:                llm.ProviderGemini,
		DisplayName:       "Google Gemini",
		Description:       "官方最新 - 推荐 Flash 极速响应 / Pro 深度代码",
		Aliases:           []string{"google"},
		RecommendedModels: []string{"gemini-2.5-flash", "gemini-2.5-pro"},
		ModelPrefixes:     []string{"gemini"},
		EnvKeys:           []string{"GEMINI_API_KEY", "GOOGLE_API_KEY"},
	},
	{
		ID:                llm.ProviderSpark,
		DisplayName:       "讯飞星辰 MaaS",
		Description:       "官方免费模型 - 默认 spark-x2.5-4b (0元/tokens无限调用) / spark-x2.5 (256K上下文)",
		Aliases:           []string{"maas", "xfyun"},
		RecommendedModels: []string{"spark-x2.5-4b", "spark-x2.5"},
		ModelPrefixes:     []string{"spark"},
		EnvKeys:           []string{"SPARK_API_KEY", "MAAS_API_KEY"},
	},
}

const (
	sparkX25Model   = "spark-x2.5"
	sparkX254BModel = "spark-x2.5-4b"
)

// Spec 是配置层合并后的厂商视图：网络事实 + 展示元数据。
type Spec struct {
	llm.Spec
	DisplayName       string
	Description       string
	Aliases           []string
	RecommendedModels []string
	ModelPrefixes     []string
	ModelSubstrings   []string
	EnvKeys           []string
}

// metaFor 返回厂商展示元数据；调用方应传入已规范的 ID。
func metaFor(p llm.Provider) providerMeta {
	for _, meta := range providerMetas {
		if meta.ID == p {
			return meta
		}
	}
	return providerMetas[0]
}

// ProviderSpec 返回厂商的静态规格（未知厂商回退到 llamacpp）。
func ProviderSpec(p llm.Provider) Spec {
	id := canonical(p)
	network, _ := llm.Lookup(id)
	meta := metaFor(id)
	return Spec{
		Spec:              network,
		DisplayName:       meta.DisplayName,
		Description:       meta.Description,
		Aliases:           append([]string(nil), meta.Aliases...),
		RecommendedModels: append([]string(nil), meta.RecommendedModels...),
		ModelPrefixes:     append([]string(nil), meta.ModelPrefixes...),
		ModelSubstrings:   append([]string(nil), meta.ModelSubstrings...),
		EnvKeys:           append([]string(nil), meta.EnvKeys...),
	}
}

// ParseProvider 把用户输入（规范 ID 或别名）解析为规范厂商。
func ParseProvider(raw string) (llm.Provider, bool) {
	s := strings.ToLower(strings.TrimSpace(raw))
	if s == "" {
		return "", false
	}
	for _, meta := range providerMetas {
		if string(meta.ID) == s {
			return meta.ID, true
		}
		for _, alias := range meta.Aliases {
			if alias == s {
				return meta.ID, true
			}
		}
	}
	return "", false
}

// ProviderIDs 返回按展示顺序排列的全部厂商规范 ID。
func ProviderIDs() []string {
	ids := make([]string, 0, len(providerMetas))
	for _, meta := range providerMetas {
		ids = append(ids, string(meta.ID))
	}
	return ids
}

// ProviderAliases 返回厂商的快捷别名列表。
func ProviderAliases(p llm.Provider) []string {
	return ProviderSpec(p).Aliases
}

// RecommendedModels 返回指定厂商官方推荐的高频常用模型列表。
func RecommendedModels(p llm.Provider) []string {
	return ProviderSpec(p).RecommendedModels
}

// ProviderDisplayName 返回厂商的友好展示名称。
func ProviderDisplayName(p llm.Provider) string {
	return ProviderSpec(p).DisplayName
}

// ProviderDescription 返回厂商的能力特征说明。
func ProviderDescription(p llm.Provider) string {
	return ProviderSpec(p).Description
}

// InferProviderFromModel 根据模型名称前缀或特征识别所属厂商，无法识别时返回空串。
func InferProviderFromModel(model string) llm.Provider {
	m := strings.ToLower(strings.TrimSpace(model))
	if m == "" {
		return ""
	}
	for _, meta := range providerMetas {
		for _, prefix := range meta.ModelPrefixes {
			if strings.HasPrefix(m, prefix) {
				return meta.ID
			}
		}
		for _, sub := range meta.ModelSubstrings {
			if strings.Contains(m, sub) {
				return meta.ID
			}
		}
	}
	return ""
}

// NormalizeModelName 归一化各厂商的模型名称，自动修复星火平台缺少 x 前缀的笔误。
func NormalizeModelName(p llm.Provider, model string) string {
	m := strings.TrimSpace(model)
	if m == "" {
		return ProviderSpec(p).DefaultModel
	}
	if canonical(p) == llm.ProviderSpark {
		switch strings.ToLower(m) {
		case "spark-2.5", "2.5":
			return sparkX25Model
		case "spark-2.5-4b", "2.5-4b", "spark-4b", "4b":
			return sparkX254BModel
		}
	}
	return m
}

// ProbeLocal 探测本地 llama.cpp 服务是否就绪。
// baseURL 可留空；允许用户传入带 /v1 的根地址。
func ProbeLocal(ctx context.Context, baseURL string) error {
	if ctx == nil {
		ctx = context.Background()
	}

	spec, _ := llm.Lookup(llm.ProviderLlamaCpp)
	base := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if base == "" {
		base = spec.BaseURL
	}
	// 用户可能已把 /v1 写进根地址，先剥离再拼探测路径，避免 /v1/v1/models
	base = strings.TrimSuffix(base, "/v1")

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, base+"/v1/models", http.NoBody)
	if err != nil {
		return err
	}

	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("本地服务探测失败，HTTP %d", resp.StatusCode)
	}
	return nil
}
