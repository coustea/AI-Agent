// Package agent 的 Token 预算控制、单向自校准与多代理用量汇总中间件（tokenBudget）。
//
// 职责：
//   - 在 BeforeModelRewriteState 中按 Eino v0.9.23 推荐方式捕获 state.ToolInfos（因 ModelContext.Tools 已弃用）；
//   - 在 WrapModel 返回的 budgetModel 中：调用前按剩余窗口动态收紧 max_tokens；
//     调用后读取供应商实际 Usage，单向上浮校准系数 scale 并写入单轮共享的 runMetrics；
//   - 通过 schema.StreamReaderWithConvert 在流式下游消费结束（EOF/Err）时零额外 goroutine 完成记账。
//
// 性能优化：
//   - BeforeModelRewriteState 不重复估算全量消息，只透传 ToolInfos；
//   - prepare 一次计算同时返回未缩放 raw 与缩放后 estimated，record 直接复用 raw 校准，避免响应后二次全量 JSON 序列化。
//
// 并发安全：tokenBudget 跨并发会话共享，scale 由 mu 保护；runMetrics 每轮 Run() 独立创建，内部仍加锁以兼容并行子代理。
package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"maps"
	"math"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"

	logutil "mentorly/internal/utils/log"
)

type (
	tokenToolsKey     struct{} // 在单次模型调用链路中透传 state.ToolInfos。
	metricsContextKey struct{} // 在单轮主代理、子代理与摘要模型间共享 runMetrics。
)

type tokenBudget struct {
	*adk.BaseChatModelAgentMiddleware
	window    int
	maxOutput int
	scope     string     // tutor / explorer / worker / summary，用于分组统计。
	mu        sync.Mutex // 保护跨并发会话共享的校准系数 scale。
	scale     float64    // 初始 1.2 保守放大；仅随真实 PromptTokens 单向上浮，绝不回调低估。
}

// newTokenBudget 为单个代理或摘要通道创建独立的预算控制器。
func newTokenBudget(window, maxOutput int, scope string) *tokenBudget {
	return &tokenBudget{
		BaseChatModelAgentMiddleware: &adk.BaseChatModelAgentMiddleware{},
		window:                       window,
		maxOutput:                    maxOutput,
		scope:                        scope,
		scale:                        1.2,
	}
}

// estimateText 同时兼顾 ASCII 与 CJK 多字节文本：
// 对 ASCII 约 3 字节/token，对 UTF-8 三字节中文额外加权，避免传统 len/4 严重低估中文消耗。
func estimateText(s string) int64 {
	return int64((len(s)+2)/3 + (len(s)-utf8.RuneCountInString(s)+1)/2)
}

// estimateTokens 估算完整请求体（消息 + 工具 schema + 固定协议开销）。
func estimateTokens(messages []*schema.Message, tools []*schema.ToolInfo) (int64, error) {
	total := int64(16)
	for _, msg := range messages {
		if msg == nil {
			return 0, fmt.Errorf("Token 统计遇到空消息")
		}
		cp := *msg
		// 剔除上次响应元数据与内部 Extra 标记，只统计真正发往模型的负载。
		cp.ResponseMeta, cp.Extra = nil, nil
		b, err := json.Marshal(&cp)
		if err != nil {
			return 0, fmt.Errorf("统计消息 Token: %w", err)
		}
		total += 12 + estimateText(string(b))
	}
	for _, info := range tools {
		if info == nil {
			continue
		}
		cp := *info
		cp.Extra = nil
		b, err := json.Marshal(&cp)
		if err != nil {
			return 0, fmt.Errorf("统计工具定义 Token: %w", err)
		}
		total += 16 + estimateText(string(b))
	}
	return total, nil
}

// countWithRaw 返回原始估算值 raw 与乘以校准系数并向上取整后的 estimated。
func (b *tokenBudget) countWithRaw(messages []*schema.Message, tools []*schema.ToolInfo) (raw, estimated int64, err error) {
	raw, err = estimateTokens(messages, tools)
	if err != nil {
		return 0, 0, err
	}
	b.mu.Lock()
	scale := b.scale
	b.mu.Unlock()
	return raw, int64(math.Ceil(float64(raw) * scale)), nil
}

// count 返回校准后的保守 Token 估算值，供 reduction 与 compaction 统一口径使用。
func (b *tokenBudget) count(messages []*schema.Message, tools []*schema.ToolInfo) (int64, error) {
	_, estimated, err := b.countWithRaw(messages, tools)
	return estimated, err
}

// outputLimit 从总窗口扣除输入与安全余量（窗口 1%，夹在 32~1024 tokens），再与配置上限取较小值。
func (b *tokenBudget) outputLimit(input int64) (int, error) {
	reserve := max(32, min(1024, b.window/100))
	available := int64(b.window) - input - int64(reserve)
	if available <= 0 {
		return 0, fmt.Errorf("%w [%s]: 估算输入 %d，窗口 %d，安全余量 %d", errContextBudget, b.scope, input, b.window, reserve)
	}
	return min(b.maxOutput, int(available)), nil
}

// BeforeModelRewriteState 仅将最新 ToolInfos 写入 ctx 供 WrapModel 消费，避免在摘要前做无用估算。
func (b *tokenBudget) BeforeModelRewriteState(ctx context.Context, state *adk.ChatModelAgentState, _ *adk.ModelContext) (context.Context, *adk.ChatModelAgentState, error) {
	return context.WithValue(ctx, tokenToolsKey{}, state.ToolInfos), state, nil
}

// WrapModel 包装底层模型；实际预算计算延迟到 Generate/Stream 时（此时摘要与所有状态改写已完成）。
func (b *tokenBudget) WrapModel(ctx context.Context, inner model.BaseChatModel, _ *adk.ModelContext) (model.BaseChatModel, error) {
	tools, _ := ctx.Value(tokenToolsKey{}).([]*schema.ToolInfo)
	return &budgetModel{inner: inner, budget: b, tools: tools}, nil
}

// budgetModel 统一封装非流式与流式调用；摘要模型也直接复用此包装层。
type budgetModel struct {
	inner  model.BaseChatModel
	budget *tokenBudget
	tools  []*schema.ToolInfo
}

// prepare 对最终入参计数并追加本次收紧后的 max_tokens；返回 raw 供 record 复用校准。
func (m *budgetModel) prepare(ctx context.Context, input []*schema.Message, opts []model.Option) ([]model.Option, int64, int64, error) {
	raw, estimated, err := m.budget.countWithRaw(input, m.tools)
	if err != nil {
		return nil, 0, 0, err
	}
	limit, err := m.budget.outputLimit(estimated)
	if err != nil {
		return nil, raw, estimated, err
	}
	logutil.FromContext(ctx, nil).Info("[Token 请求预算]",
		zap.String("scope", m.budget.scope),
		zap.Int64("estimated_input_tokens", estimated),
		zap.Int("max_output_tokens", limit),
		zap.Int("context_window", m.budget.window),
	)
	if metrics, _ := ctx.Value(metricsContextKey{}).(*runMetrics); metrics != nil {
		metrics.mu.Lock()
		metrics.modelCalls++
		metrics.mu.Unlock()
	}
	// 复制选项切片后再追加，确保不污染外层重试或共享选项，且本次上限优先生效。
	return append(append([]model.Option(nil), opts...), model.WithMaxTokens(limit)), raw, estimated, nil
}

// record 仅采信供应商真实返回的 Usage：单向上浮校准系数并累加到单轮指标。
func (m *budgetModel) record(ctx context.Context, output *schema.Message, raw, estimated int64, started time.Time) {
	if output == nil || output.ResponseMeta == nil || output.ResponseMeta.Usage == nil {
		return
	}
	usage := output.ResponseMeta.Usage
	if raw > 0 && usage.PromptTokens > 0 {
		// 单向上浮并留 10% 余量，防止偶发低 Usage 拉低系数导致后续超窗。
		m.budget.mu.Lock()
		m.budget.scale = max(m.budget.scale, float64(usage.PromptTokens)/float64(raw)*1.1)
		m.budget.mu.Unlock()
	}
	fields := append(usageLogFields(output, time.Since(started).Milliseconds()),
		zap.String("scope", m.budget.scope),
		zap.Int64("estimated_input_tokens", estimated),
	)
	logutil.FromContext(ctx, nil).Info("[Token 实际用量]", fields...)
	if metrics, _ := ctx.Value(metricsContextKey{}).(*runMetrics); metrics != nil {
		metrics.addUsage(m.budget.scope, usage)
	}
}

func (m *budgetModel) Generate(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.Message, error) {
	options, raw, estimated, err := m.prepare(ctx, input, opts)
	if err != nil {
		return nil, err
	}
	started := time.Now()
	output, err := m.inner.Generate(ctx, input, options...)
	m.record(ctx, output, raw, estimated, started)
	return output, err
}

func (m *budgetModel) Stream(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	options, raw, estimated, err := m.prepare(ctx, input, opts)
	if err != nil {
		return nil, err
	}
	started := time.Now()
	stream, err := m.inner.Stream(ctx, input, options...)
	if err != nil {
		return nil, err
	}
	// 流式 Usage 通常只在末尾分片携带，保留最后一份并用 sync.Once 保证只记账一次。
	var last *schema.Message
	var once sync.Once
	record := func() { once.Do(func() { m.record(ctx, last, raw, estimated, started) }) }
	return schema.StreamReaderWithConvert(
		stream,
		func(msg *schema.Message) (*schema.Message, error) {
			if msg != nil && msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil {
				last = msg
			}
			return msg, nil
		},
		schema.WithOnEOF(func() (any, error) { record(); return nil, io.EOF }),
		schema.WithErrWrapper(func(err error) error { record(); return err }),
	), nil
}

// runMetrics 按 scope（tutor / explorer / worker / summary）汇总单轮所有模型调用消耗。
type runMetrics struct {
	mu          sync.Mutex
	modelCalls  int
	scopedUsage map[string]schema.TokenUsage
}

func (m *runMetrics) addUsage(scope string, u *schema.TokenUsage) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.scopedUsage == nil {
		m.scopedUsage = make(map[string]schema.TokenUsage)
	}
	total := m.scopedUsage[scope]
	total.PromptTokens += u.PromptTokens
	total.CompletionTokens += u.CompletionTokens
	total.CompletionTokensDetails.ReasoningTokens += u.CompletionTokensDetails.ReasoningTokens
	total.TotalTokens += u.TotalTokens
	m.scopedUsage[scope] = total
}

func (m *runMetrics) SummaryFields(elapsed time.Duration) []zap.Field {
	m.mu.Lock()
	defer m.mu.Unlock()
	var total schema.TokenUsage
	for _, u := range m.scopedUsage {
		total.PromptTokens += u.PromptTokens
		total.CompletionTokens += u.CompletionTokens
		total.CompletionTokensDetails.ReasoningTokens += u.CompletionTokensDetails.ReasoningTokens
		total.TotalTokens += u.TotalTokens
	}
	return []zap.Field{
		zap.Int64("elapsed_ms", elapsed.Milliseconds()),
		zap.Int("model_calls", m.modelCalls),
		zap.Int("prompt_tokens", total.PromptTokens),
		zap.Int("completion_tokens", total.CompletionTokens),
		zap.Int("reasoning_tokens", total.CompletionTokensDetails.ReasoningTokens),
		zap.Int("total_tokens", total.TotalTokens),
		zap.Any("usage_by_scope", maps.Clone(m.scopedUsage)),
	}
}

// usageLogFields 构造模型响应观测字段；思考内容只记字符数，不记录正文。
func usageLogFields(msg *schema.Message, elapsedMS int64) []zap.Field {
	reason := "未提供"
	if msg != nil && msg.ResponseMeta != nil {
		if r := strings.TrimSpace(msg.ResponseMeta.FinishReason); r != "" {
			reason = r
		}
	}
	fields := []zap.Field{zap.String("finish_reason", reason)}
	if elapsedMS > 0 {
		fields = append(fields, zap.Int64("model_elapsed_ms", elapsedMS))
	}
	if msg == nil {
		return fields
	}
	fields = append(fields,
		zap.Int("reasoning_chars", utf8.RuneCountInString(msg.ReasoningContent)),
		zap.Int("content_chars", utf8.RuneCountInString(msg.Content)),
		zap.Int("tool_calls", len(msg.ToolCalls)),
	)
	if msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil {
		u := msg.ResponseMeta.Usage
		fields = append(fields,
			zap.Int("prompt_tokens", u.PromptTokens),
			zap.Int("completion_tokens", u.CompletionTokens),
			zap.Int("reasoning_tokens", u.CompletionTokensDetails.ReasoningTokens),
			zap.Int("total_tokens", u.TotalTokens),
		)
	}
	return fields
}
