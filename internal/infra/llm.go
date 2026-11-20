// 本文件负责 eino ChatModel 的初始化与供应商适配。
// 供应商差异收敛在本包内，不向上层（service / handler）泄露。
package infra

import (
	"context"
	"fmt"
	"net/url"
	"strings"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"

	"mentorly/internal/config"
)

// Provider 模型供应商
type Provider string

const (
	// ProviderOpenAI 走 OpenAI 兼容协议（Spark、DeepSeek、通义、Kimi 等均可）
	ProviderOpenAI Provider = "openai"
	// ProviderSpark 讯飞星火，本质也是 OpenAI 兼容协议，单独列出便于写默认值
	ProviderSpark Provider = "spark"
)

// NewModel 按配置构建 eino ChatModel。
// 未配置 api_key 时返回 (nil, nil)，表示不启用 AI 能力，由上层决定降级行为。
func NewModel(ctx context.Context, cfg config.LLMConfig) (model.ToolCallingChatModel, error) {
	// 未配置密钥视为「不启用」，不是错误，避免本地无 key 时无法启动。
	if strings.TrimSpace(cfg.APIKey) == "" {
		return nil, nil
	}

	switch Provider(strings.ToLower(strings.TrimSpace(cfg.Provider))) {
	case ProviderSpark:
		return newSpark(ctx, cfg)
	case ProviderOpenAI, "":
		return newOpenAI(ctx, cfg)
	default:
		return nil, fmt.Errorf("不支持的 llm.provider: %s", cfg.Provider)
	}
}

// newSpark 构造星火模型。
//
// 与 openai 的差别只在默认值：BaseURL 与模型名有内置缺省，
// 且允许通过 extra_fields 传 thinking 等供应商扩展参数。
func newSpark(ctx context.Context, cfg config.LLMConfig) (model.ToolCallingChatModel, error) {
	const (
		defaultBaseURL = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
		defaultModel   = "spark-x2.6"
	)

	c := cfg
	if strings.TrimSpace(c.BaseURL) == "" {
		c.BaseURL = defaultBaseURL
	}
	if strings.TrimSpace(c.Model) == "" {
		c.Model = defaultModel
	}
	return newOpenAI(ctx, c)
}

func newOpenAI(ctx context.Context, cfg config.LLMConfig) (model.ToolCallingChatModel, error) {
	baseURL, err := normalizeBaseURL(cfg.BaseURL)
	if err != nil {
		return nil, err
	}

	conf := &openai.ChatModelConfig{
		BaseURL: baseURL,
		APIKey:  strings.TrimSpace(cfg.APIKey),
		Model:   strings.TrimSpace(cfg.Model),
	}

	// 只透传非零值，避免把 nil/0 覆盖服务端默认行为。
	if cfg.MaxToken > 0 {
		conf.MaxTokens = &cfg.MaxToken
	}
	if cfg.Timeout > 0 {
		conf.Timeout = cfg.Timeout
	}
	// 供应商扩展参数原样透传（如 temperature / top_p / thinking）。
	if len(cfg.ExtraFields) > 0 {
		conf.ExtraFields = cfg.ExtraFields
	}

	cm, err := openai.NewChatModel(ctx, conf)
	if err != nil {
		return nil, fmt.Errorf("初始化 eino ChatModel 失败: %w", err)
	}

	return cm, nil
}

// normalizeBaseURL 校验并归一化 BaseURL。
//
// eino 的 openai 组件会自己在 BaseURL 后拼接 /chat/completions，
// 因此这里必须拒绝带该后缀的地址——否则实际请求会变成
// /v2/chat/completions/chat/completions 而 404。
// HyperWeaver 的配置里 .env 就填的是完整地址，这里提前给出明确报错。
func normalizeBaseURL(raw string) (string, error) {
	base := strings.TrimRight(strings.TrimSpace(raw), "/")
	if base == "" {
		return "", fmt.Errorf("llm.base_url 不能为空")
	}

	u, err := url.Parse(base)
	if err != nil {
		return "", fmt.Errorf("llm.base_url 无法解析: %w", err)
	}
	if u.Hostname() == "" || (u.Scheme != "http" && u.Scheme != "https") {
		return "", fmt.Errorf("llm.base_url 必须是 http(s) 绝对地址，当前 %q", raw)
	}
	if strings.HasSuffix(strings.ToLower(u.Path), "/chat/completions") {
		return "", fmt.Errorf(
			"llm.base_url 不能包含 /chat/completions（eino 会自行拼接），"+
				"请改为 %q",
			strings.TrimSuffix(base, "/chat/completions"),
		)
	}

	return base, nil
}

// Completer 把 eino ChatModel 适配成「给一段文本、拿一段文本」的简单接口，
// 供 memory 包的压缩与记忆整合使用。
type Completer struct {
	model model.ToolCallingChatModel
}

// NewCompleter 构造适配器。cm 为 nil 时返回 nil，表示未启用 LLM 能力。
func NewCompleter(cm model.ToolCallingChatModel) *Completer {
	if cm == nil {
		return nil
	}
	return &Completer{model: cm}
}

// Complete 走一次非流式生成。
//
// 摘要与整合都属于「忠实改写」任务，同时需要稳定的结构化输出，
// 所以统一用低温；这里不暴露 temperature 参数，避免调用方各自为政。
func (c *Completer) Complete(ctx context.Context, system, user string) (string, error) {
	if c == nil || c.model == nil {
		return "", fmt.Errorf("LLM 未配置")
	}

	var temp float32 = 0.2
	msgs := []*schema.Message{
		schema.SystemMessage(system),
		schema.UserMessage(user),
	}

	resp, err := c.model.Generate(ctx, msgs, model.WithTemperature(temp))
	if err != nil {
		return "", fmt.Errorf("LLM 生成失败: %w", err)
	}
	if resp == nil {
		return "", fmt.Errorf("LLM 返回空响应")
	}

	return resp.Content, nil
}
