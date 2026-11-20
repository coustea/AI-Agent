package runtime

import (
	"context"
	"fmt"
	"net/url"
	"strings"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"
)

// ModelConfig 是构建 ChatModel 所需的最小参数集。
// 刻意不使用 internal/config 的类型，使本包可以脱离配置文件单测。
type ModelConfig struct {
	Provider string
	Model    string
	BaseURL  string
	APIKey   string
	MaxToken int
	Timeout  int64 // 秒
	Extra    map[string]any
	Vision   bool
}

// NewModel 按配置构建 Eino ChatModel。
// 未配置 api_key 时返回 (nil, nil)：AI 能力未启用，由上层返回 503，
// 这是唯一允许的「未启用」表达方式，不会退化成 Mock。
func NewModel(ctx context.Context, cfg ModelConfig) (model.ToolCallingChatModel, error) {
	if strings.TrimSpace(cfg.APIKey) == "" {
		return nil, nil
	}

	switch strings.ToLower(strings.TrimSpace(cfg.Provider)) {
	case "spark":
		if strings.TrimSpace(cfg.BaseURL) == "" {
			cfg.BaseURL = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
		}
		if strings.TrimSpace(cfg.Model) == "" {
			cfg.Model = "spark-x2.6"
		}
		return newOpenAIModel(ctx, cfg)
	case "openai", "":
		return newOpenAIModel(ctx, cfg)
	default:
		return nil, fmt.Errorf("不支持的 llm.provider: %s", cfg.Provider)
	}
}

func newOpenAIModel(ctx context.Context, cfg ModelConfig) (model.ToolCallingChatModel, error) {
	baseURL, err := NormalizeBaseURL(cfg.BaseURL)
	if err != nil {
		return nil, err
	}

	conf := &openai.ChatModelConfig{
		BaseURL: baseURL,
		APIKey:  strings.TrimSpace(cfg.APIKey),
		Model:   strings.TrimSpace(cfg.Model),
	}
	if cfg.MaxToken > 0 {
		conf.MaxTokens = &cfg.MaxToken
	}
	if cfg.Timeout > 0 {
		conf.Timeout = timeDuration(cfg.Timeout)
	}
	if len(cfg.Extra) > 0 {
		conf.ExtraFields = cfg.Extra
	}

	cm, err := openai.NewChatModel(ctx, conf)
	if err != nil {
		return nil, fmt.Errorf("初始化 eino ChatModel 失败: %w", err)
	}
	return cm, nil
}

// NormalizeBaseURL 校验并归一化 OpenAI 兼容接口地址。
// eino 会自行拼接 /chat/completions，因此这里拒绝已经带该后缀的地址，
// 否则请求会变成 .../chat/completions/chat/completions 并返回 404。
func NormalizeBaseURL(raw string) (string, error) {
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
			"llm.base_url 不能包含 /chat/completions（eino 会自行拼接），请改为 %q",
			strings.TrimSuffix(base, "/chat/completions"),
		)
	}
	return base, nil
}

// Complete 走一次非流式生成，供会话标题等确定性文本任务使用。
// 标题与摘要都是「忠实改写」任务，需要稳定输出，因此统一用低温。
func Complete(ctx context.Context, cm model.ToolCallingChatModel, system, user string) (string, error) {
	if cm == nil {
		return "", ErrNotConfigured
	}
	var temp float32 = 0.2
	resp, err := cm.Generate(ctx, []*schema.Message{
		schema.SystemMessage(system),
		schema.UserMessage(user),
	}, model.WithTemperature(temp))
	if err != nil {
		return "", fmt.Errorf("LLM 生成失败: %w", err)
	}
	if resp == nil {
		return "", fmt.Errorf("LLM 返回空响应")
	}
	return resp.Content, nil
}
