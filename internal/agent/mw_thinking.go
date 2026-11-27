// Package agent 的思考模式路由中间件（thinkingMode）。
//
// 职责：
//   - 按配置策略（first_call_only / always / disabled / off）向已验证支持该协议的供应商（目前为 Spark）
//     按调用注入 thinking 参数，平衡首步规划深度与后续工具循环延迟；
//   - 在 first_call_only 模式下通过 Eino RunLocal 隔离每轮状态：仅本轮首次模型调用开启思考，后续调用自动关闭。
//
// 并发安全：中间件本身只存不可变选项切片，状态完全存储在单次运行的 ctx RunLocal 中。
package agent

import (
	"context"
	"maps"
	"strings"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"
)

const (
	thinkingFirstCallOnly = "first_call_only"
	thinkingAlways        = "always"
	thinkingDisabled      = "disabled"
	thinkingOff           = "off"

	thinkingUsedKey = "mentorly:thinking_used"
)

type thinkingMode struct {
	*adk.BaseChatModelAgentMiddleware
	mode         string
	enabledOpts  []model.Option
	disabledOpts []model.Option
}

var _ adk.ChatModelAgentMiddleware = (*thinkingMode)(nil)

// newThinking 预构造思考开/关两组不可变 Option；非 Spark 供应商或 off 模式均保持零干预透传。
func newThinking(mode, provider string, baseExtra map[string]any) *thinkingMode {
	mode = strings.ToLower(strings.TrimSpace(mode))
	if mode == "" {
		mode = thinkingFirstCallOnly
	}
	mw := &thinkingMode{
		BaseChatModelAgentMiddleware: &adk.BaseChatModelAgentMiddleware{},
		mode:                         mode,
	}
	if mode == thinkingOff {
		return mw
	}
	if strings.EqualFold(strings.TrimSpace(provider), "spark") {
		mw.enabledOpts = []model.Option{buildThinkingOption(baseExtra, "enabled")}
		mw.disabledOpts = []model.Option{buildThinkingOption(baseExtra, "disabled")}
	}
	return mw
}

// buildThinkingOption 在基础 ExtraFields 副本上覆写 thinking 字段，避免丢失其他供应商参数。
func buildThinkingOption(base map[string]any, thinkingType string) model.Option {
	merged := make(map[string]any, len(base)+1)
	maps.Copy(merged, base)
	merged["thinking"] = map[string]any{"type": thinkingType}
	return openai.WithExtraFields(merged)
}

// WrapModel 在不修改共享底层 ChatModel 的前提下，为本次调用选择思考选项。
func (t *thinkingMode) WrapModel(ctx context.Context, m model.BaseChatModel, _ *adk.ModelContext) (model.BaseChatModel, error) {
	if t == nil || t.mode == thinkingOff || len(t.enabledOpts)+len(t.disabledOpts) == 0 {
		return m, nil
	}
	var extra []model.Option
	switch t.mode {
	case thinkingAlways:
		extra = t.enabledOpts
	case thinkingDisabled:
		extra = t.disabledOpts
	case thinkingFirstCallOnly:
		extra = t.disabledOpts
		if used, _, err := adk.GetRunLocalValue(ctx, thinkingUsedKey); err == nil && used != true {
			if err := adk.SetRunLocalValue(ctx, thinkingUsedKey, true); err == nil {
				extra = t.enabledOpts
			}
		}
	default:
		return m, nil
	}
	if len(extra) == 0 {
		return m, nil
	}
	return &optionInjectingModel{inner: m, extra: extra}, nil
}

type optionInjectingModel struct {
	inner model.BaseChatModel
	extra []model.Option
}

func (m *optionInjectingModel) Generate(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.Message, error) {
	return m.inner.Generate(ctx, input, append(append([]model.Option(nil), opts...), m.extra...)...)
}

func (m *optionInjectingModel) Stream(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	return m.inner.Stream(ctx, input, append(append([]model.Option(nil), opts...), m.extra...)...)
}
