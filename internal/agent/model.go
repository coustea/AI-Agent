// Package agent 的模型接入与 HTTP/SSE 传输保护层。
//
// 职责：
//   - 按配置构建 Eino OpenAI 兼容 ChatModel（支持 Spark 与通用 OpenAI 供应商）；
//   - 规范化 API BaseURL，防止重复拼接 /chat/completions；
//   - 在传输层提供分片级 SSE 空闲超时（streamIdleTransport + idleTimeoutBody），
//     弥补标准库 http.Transport.ResponseHeaderTimeout 无法覆盖响应头返回后静默挂死的缺口。
//
// 并发安全：NewModel 返回的 ChatModel 与底层 Transport 可被多个并发会话共享。
package agent

import (
	"cmp"
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/components/model"
)

const defaultIdleTimeout = 60 * time.Second

// ErrStreamIdleTimeout 在上游返回 HTTP 200 响应头后，连续超过 idleTimeout 未读到任何字节时返回。
// 与整轮 context.DeadlineExceeded 区分，便于 isTransient 标记可重试并在局部工具中自愈。
var ErrStreamIdleTimeout = errors.New("模型流式响应空闲超时")

// ModelConfig 描述底层模型连接参数；上下文窗口与单次输出预算由 tokenBudget 中间件管理。
type ModelConfig struct {
	Provider string
	Model    string
	BaseURL  string
	APIKey   string
	MaxToken int
	Timeout  time.Duration  // 同时约束响应头等待时长与 SSE 分片间最大静默时长。
	Extra    map[string]any // 透传供应商扩展参数，例如 Spark 的 thinking 配置。
}

// NewModel 按配置构建 Eino ChatModel；未配置 APIKey 时返回 (nil, nil)，允许服务以降级态启动。
func NewModel(ctx context.Context, cfg ModelConfig) (model.ToolCallingChatModel, error) {
	if strings.TrimSpace(cfg.APIKey) == "" {
		return nil, nil
	}
	switch strings.ToLower(strings.TrimSpace(cfg.Provider)) {
	case "spark":
		cfg.BaseURL = cmp.Or(strings.TrimSpace(cfg.BaseURL), "https://maas-api.cn-huabei-1.xf-yun.com/v2")
		cfg.Model = cmp.Or(strings.TrimSpace(cfg.Model), "spark-x2.6")
	case "openai", "":
	default:
		return nil, fmt.Errorf("不支持的 llm.provider: %s", cfg.Provider)
	}

	baseURL, err := normalizeBaseURL(cfg.BaseURL)
	if err != nil {
		return nil, err
	}
	idleTimeout := cmp.Or(cfg.Timeout, defaultIdleTimeout)
	if idleTimeout <= 0 {
		idleTimeout = defaultIdleTimeout
	}

	// 克隆默认 Transport，避免污染全局连接池：
	// 1) ResponseHeaderTimeout 防止建连后迟迟不返回响应头；
	// 2) streamIdleTransport 防止返回 HTTP 200 text/event-stream 后首包或中途分片静默挂死，
	//    同时不影响正常持续输出的长流式响应（不可使用 http.Client.Timeout，它会硬杀长流）。
	transport := http.DefaultTransport.(*http.Transport).Clone()
	transport.ResponseHeaderTimeout = idleTimeout

	conf := &openai.ChatModelConfig{
		BaseURL:     baseURL,
		APIKey:      strings.TrimSpace(cfg.APIKey),
		Model:       strings.TrimSpace(cfg.Model),
		HTTPClient:  &http.Client{Transport: &streamIdleTransport{base: transport, idleTimeout: idleTimeout}},
		ExtraFields: cfg.Extra,
	}
	if cfg.MaxToken > 0 {
		// 默认输出上限；每次请求前还会被 tokenBudget 按剩余窗口动态收紧。
		conf.MaxTokens = &cfg.MaxToken
	}
	cm, err := openai.NewChatModel(ctx, conf)
	if err != nil {
		return nil, fmt.Errorf("初始化 eino ChatModel 失败: %w", err)
	}
	return cm, nil
}

// streamIdleTransport 为每次 HTTP 响应体挂载逐 Read 刷新的空闲超时守护。
type streamIdleTransport struct {
	base        http.RoundTripper
	idleTimeout time.Duration
}

func (t *streamIdleTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	// 派生可带原因取消的请求 context：当某次 Read 超时，通过 cancel(ErrStreamIdleTimeout)
	// 主动打断阻塞中的底层连接，再由 Read 统一翻译为 ErrStreamIdleTimeout 返回。
	ctx, cancel := context.WithCancelCause(req.Context())
	resp, err := t.base.RoundTrip(req.WithContext(ctx))
	if err != nil {
		cancel(nil)
		return nil, err
	}
	if resp == nil || resp.Body == nil || t.idleTimeout <= 0 {
		cancel(nil)
		return resp, nil
	}
	resp.Body = &idleTimeoutBody{rc: resp.Body, reqCtx: ctx, timeout: t.idleTimeout, cancel: cancel}
	return resp, nil
}

// idleTimeoutBody 在每次 Read 期间启动一次性定时器，收到任意字节即停止，
// 从而只惩罚“静默挂死”而不限制健康长流的总耗时。
type idleTimeoutBody struct {
	rc      io.ReadCloser
	reqCtx  context.Context
	timeout time.Duration
	cancel  context.CancelCauseFunc
	once    sync.Once
}

func (b *idleTimeoutBody) Read(p []byte) (int, error) {
	timer := time.AfterFunc(b.timeout, func() { b.cancel(ErrStreamIdleTimeout) })
	n, err := b.rc.Read(p)
	timer.Stop()
	if err != nil && errors.Is(context.Cause(b.reqCtx), ErrStreamIdleTimeout) {
		return n, ErrStreamIdleTimeout
	}
	return n, err
}

func (b *idleTimeoutBody) Close() error {
	// 必须确保 cancel 被调用以释放 context 树中的取消监听，sync.Once 保证幂等关闭。
	b.once.Do(func() { b.cancel(nil) })
	return b.rc.Close()
}

// normalizeBaseURL 仅接受 API 根地址；具体 /chat/completions 路径由 Eino OpenAI 适配器补齐。
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
		return "", fmt.Errorf("llm.base_url 不能包含 /chat/completions（eino 会自行拼接），请改为 %q", strings.TrimSuffix(base, "/chat/completions"))
	}
	return base, nil
}
