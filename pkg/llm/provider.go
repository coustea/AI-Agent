package llm

import (
	"net/http"
	"strings"
)

// Provider 是模型厂商标识（规范 ID）。
type Provider string

const (
	ProviderDeepSeek Provider = "deepseek"
	ProviderGemini   Provider = "gemini"
	ProviderSpark    Provider = "spark"
	ProviderLlamaCpp Provider = "llamacpp"
	ProviderOpenAI   Provider = "openai"
	ProviderCustom   Provider = "custom"
)

// AuthKind 声明凭据的注入方式。
type AuthKind uint8

const (
	AuthBearer    AuthKind = iota // Authorization: Bearer <key>
	AuthGoogleKey                 // x-goog-api-key: <key>
)

// Spec 描述一个厂商的全部网络事实。新增厂商只需在 specs 表里加一行。
type Spec struct {
	ID           Provider
	BaseURL      string // 默认根地址（不含端点路径）
	ChatPath     string // 相对根地址的 chat completions 路径
	DefaultModel string
	Auth         AuthKind
	Local        bool // 本地服务，API Key 可空
}

// specs 是全部厂商网络事实的唯一注册表。
var specs = []Spec{
	{
		ID:           ProviderDeepSeek,
		BaseURL:      "https://api.deepseek.com",
		ChatPath:     "/v1/chat/completions",
		DefaultModel: "deepseek-flash",
		Auth:         AuthBearer,
	},
	{
		ID:           ProviderGemini,
		BaseURL:      "https://generativelanguage.googleapis.com/v1beta/openai",
		ChatPath:     "/chat/completions",
		DefaultModel: "gemini-2.5-flash",
		Auth:         AuthGoogleKey,
	},
	{
		ID:           ProviderSpark,
		BaseURL:      "https://maas-api.cn-huabei-1.xf-yun.com/v2",
		ChatPath:     "/chat/completions",
		DefaultModel: "spark-x2.5-4b",
		Auth:         AuthBearer,
	},
	{
		ID:           ProviderLlamaCpp,
		BaseURL:      "http://127.0.0.1:8080",
		ChatPath:     "/v1/chat/completions",
		DefaultModel: "local-model",
		Auth:         AuthBearer,
		Local:        true,
	},
}

// Specs 返回全部厂商规格的副本。
func Specs() []Spec {
	out := make([]Spec, len(specs))
	copy(out, specs)
	return out
}

// Lookup 按规范 ID 查找厂商规格；不做别名解析。
func Lookup(p Provider) (Spec, bool) {
	for _, s := range specs {
		if s.ID == p {
			return s, true
		}
	}
	return Spec{}, false
}

// endpoint 拼接完整 chat completions 地址。
// 智能自适应末尾路径，兼容用户输入纯域名、以 /v1 结尾或已包含完整 /chat/completions 的情况。
func (s Spec) endpoint(baseURL string) string {
	base := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if base == "" {
		base = s.BaseURL
	}
	if strings.HasSuffix(base, "/chat/completions") {
		return base
	}
	if strings.HasSuffix(base, "/v1") {
		return base + "/chat/completions"
	}
	chatPath := s.ChatPath
	if chatPath == "" {
		chatPath = "/v1/chat/completions"
	}
	if !strings.HasPrefix(chatPath, "/") {
		chatPath = "/" + chatPath
	}
	return base + chatPath
}

// authorize 按厂商约定注入鉴权头；key 为空时不做任何注入。
func (s Spec) authorize(req *http.Request, apiKey string) {
	key := strings.TrimSpace(apiKey)
	if key == "" {
		return
	}
	switch s.Auth {
	case AuthGoogleKey:
		req.Header.Set("x-goog-api-key", key)
	default:
		req.Header.Set("Authorization", "Bearer "+key)
	}
}
