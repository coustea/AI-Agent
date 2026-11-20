package runtime

import (
	"context"
	"io"
	"time"

	"github.com/cloudwego/eino/callbacks"
	"github.com/cloudwego/eino/components"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"
)

func timeDuration(seconds int64) time.Duration {
	return time.Duration(seconds) * time.Second
}

type callbackStartKey struct{}

// NewCallbackHandler 构建 Eino Callback Handler：
// 记录模型/工具调用耗时、真实 Token 用量与错误，不参与业务决策。
//
// 这是全系统唯一的可观测性注入点：Agent 与 Capability 都不自己打点，
// 避免同一件事在多个模块里各记一遍、口径还不一致。
func NewCallbackHandler(log *zap.Logger) callbacks.Handler {
	if log == nil {
		log = zap.NewNop()
	}

	started := func(ctx context.Context) context.Context {
		return context.WithValue(ctx, callbackStartKey{}, time.Now())
	}
	elapsed := func(ctx context.Context) time.Duration {
		if t, ok := ctx.Value(callbackStartKey{}).(time.Time); ok {
			return time.Since(t)
		}
		return 0
	}

	return callbacks.NewHandlerBuilder().
		OnStartFn(func(ctx context.Context, info *callbacks.RunInfo, input callbacks.CallbackInput) context.Context {
			if info == nil {
				return ctx
			}
			switch info.Component {
			case components.ComponentOfChatModel:
				if in := model.ConvCallbackInput(input); in != nil {
					log.Debug("模型调用开始",
						zap.String("model", info.Name),
						zap.Int("messages", len(in.Messages)),
						zap.Int("tools", len(in.Tools)),
					)
				}
			case components.ComponentOfTool:
				if in := tool.ConvCallbackInput(input); in != nil {
					log.Debug("工具调用开始",
						zap.String("tool", info.Name),
						zap.Int("args_chars", len(in.ArgumentsInJSON)),
					)
				}
			}
			return started(ctx)
		}).
		OnEndFn(func(ctx context.Context, info *callbacks.RunInfo, output callbacks.CallbackOutput) context.Context {
			if info == nil {
				return ctx
			}
			switch info.Component {
			case components.ComponentOfChatModel:
				out := model.ConvCallbackOutput(output)
				if out != nil && out.TokenUsage != nil {
					log.Info("模型调用完成",
						zap.String("model", info.Name),
						zap.Duration("elapsed", elapsed(ctx)),
						zap.Int("prompt_tokens", out.TokenUsage.PromptTokens),
						zap.Int("completion_tokens", out.TokenUsage.CompletionTokens),
						zap.Int("total_tokens", out.TokenUsage.TotalTokens),
					)
				}
			case components.ComponentOfTool:
				log.Info("工具调用完成",
					zap.String("tool", info.Name),
					zap.Duration("elapsed", elapsed(ctx)),
				)
			}
			return ctx
		}).
		OnErrorFn(func(ctx context.Context, info *callbacks.RunInfo, err error) context.Context {
			if info != nil {
				log.Warn("组件调用失败",
					zap.String("component", string(info.Component)),
					zap.String("name", info.Name),
					zap.Error(err),
				)
			}
			return ctx
		}).
		OnStartWithStreamInputFn(func(ctx context.Context, info *callbacks.RunInfo, input *schema.StreamReader[callbacks.CallbackInput]) context.Context {
			if input != nil {
				go drainCallbackStream(input, nil, nil)
			}
			return started(ctx)
		}).
		OnEndWithStreamOutputFn(func(ctx context.Context, info *callbacks.RunInfo, output *schema.StreamReader[callbacks.CallbackOutput]) context.Context {
			if output != nil {
				go drainCallbackStream(output, info, func(info *callbacks.RunInfo, out callbacks.CallbackOutput) {
					if info == nil || info.Component != components.ComponentOfChatModel {
						return
					}
					mo := model.ConvCallbackOutput(out)
					if mo == nil || mo.TokenUsage == nil {
						return
					}
					log.Info("模型流式调用完成",
						zap.String("model", info.Name),
						zap.Int("prompt_tokens", mo.TokenUsage.PromptTokens),
						zap.Int("completion_tokens", mo.TokenUsage.CompletionTokens),
						zap.Int("total_tokens", mo.TokenUsage.TotalTokens),
					)
				})
			}
			return ctx
		}).
		Build()
}

// drainCallbackStream 消费框架给出的独立回调流，防止 goroutine 泄漏。
func drainCallbackStream[T any](sr *schema.StreamReader[T], info *callbacks.RunInfo, onItem func(*callbacks.RunInfo, T)) {
	defer sr.Close()
	for {
		item, err := sr.Recv()
		if err != nil {
			if err != io.EOF {
				_ = err
			}
			return
		}
		if onItem != nil {
			onItem(info, item)
		}
	}
}
