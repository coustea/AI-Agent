// Package middleware 存放 TutorAgent 的自定义 Middleware。
//
// 只实现 Eino 官方没有覆盖的业务约束：工具级权限与副作用校验。
// 日志、Trace、Token 统计、上下文压缩、技能加载全部使用官方实现，
// 不在本包重复造轮子。
package middleware

import (
	"context"
	"errors"
	"fmt"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"

	"mentorly/internal/runtime"
)

// ErrToolDenied 工具调用被拒绝。
var ErrToolDenied = errors.New("工具调用被拒绝")

// 需要运行身份的约束。
//
// 这些工具全部要读写用户数据，没有 Principal 就必须拒绝执行：
// 让它们在没有身份的情况下跑起来，等价于把用户隔离交给模型自觉。
var requiresPrincipal = map[string]bool{
	"memory_search":            true,
	"memory_save":              true,
	"memory_delete":            true,
	"read_attachment":          true,
	"list_attachments":         true,
	"generate_diagram":         true,
	"generate_presentation":    true,
	"generate_explainer_video": true,
	"get_artifact_status":      true,
}

// 单轮内调用次数上限。
//
// 目的不是限制能力，而是拦住模型陷入「反复生成同类产物」的死循环——
// 这类循环会真的消耗大量算力（视频渲染尤其昂贵），
// 仅靠 MaxIterations 只能在轮次层面兜底。
var callBudget = map[string]int{
	"generate_diagram":         6,
	"generate_presentation":    4,
	"generate_explainer_video": 3,
}

// ToolGuard 是工具调用的权限与配额守卫。
//
// 必须同时覆盖四种工具类型：
//   - InvokableTool
//   - StreamableTool
//   - EnhancedInvokableTool
//   - EnhancedStreamableTool
//
// 只拦其中一两种却宣称「所有工具都受保护」是典型的安全假象：
// 框架按工具实际实现的接口分发，漏掉哪个类型，那个类型的工具就完全绕过校验。
type ToolGuard struct {
	*adk.BaseChatModelAgentMiddleware
	log *zap.Logger
}

// NewToolGuard 构造守卫。
func NewToolGuard(log *zap.Logger) *ToolGuard {
	if log == nil {
		log = zap.NewNop()
	}
	return &ToolGuard{
		BaseChatModelAgentMiddleware: &adk.BaseChatModelAgentMiddleware{},
		log:                          log,
	}
}

// check 是四种 Wrap 共用的校验逻辑。
func (g *ToolGuard) check(ctx context.Context, tCtx *adk.ToolContext) error {
	name := ""
	if tCtx != nil {
		name = tCtx.Name
	}

	// 1. 身份校验：需要用户数据的工具必须有 Principal。
	if requiresPrincipal[name] {
		if _, ok := runtime.PrincipalFrom(ctx); !ok {
			return fmt.Errorf("%w: 工具 %s 需要已认证用户上下文", ErrToolDenied, name)
		}
	}

	// 2. 配额校验：按运行隔离的计数器。
	if limit, ok := callBudget[name]; ok {
		if p, ok := runtime.PrincipalFrom(ctx); ok && p != nil {
			if n := runtime.CountToolCall(ctx, name); n >= limit {
				return fmt.Errorf("%w: 工具 %s 本轮已调用 %d 次，达到上限 %d 次",
					ErrToolDenied, name, n, limit)
			}
		}
	}

	return nil
}

// WrapInvokableToolCall 拦截同步工具。
func (g *ToolGuard) WrapInvokableToolCall(ctx context.Context, endpoint adk.InvokableToolCallEndpoint, tCtx *adk.ToolContext) (adk.InvokableToolCallEndpoint, error) {
	return func(ctx context.Context, argumentsInJSON string, opts ...tool.Option) (string, error) {
		if err := g.check(ctx, tCtx); err != nil {
			g.deny(tCtx, err)
			return "", err
		}
		return endpoint(ctx, argumentsInJSON, opts...)
	}, nil
}

// WrapStreamableToolCall 拦截流式工具。
func (g *ToolGuard) WrapStreamableToolCall(ctx context.Context, endpoint adk.StreamableToolCallEndpoint, tCtx *adk.ToolContext) (adk.StreamableToolCallEndpoint, error) {
	return func(ctx context.Context, argumentsInJSON string, opts ...tool.Option) (*schema.StreamReader[string], error) {
		if err := g.check(ctx, tCtx); err != nil {
			g.deny(tCtx, err)
			return nil, err
		}
		return endpoint(ctx, argumentsInJSON, opts...)
	}, nil
}

// WrapEnhancedInvokableToolCall 拦截增强同步工具。
func (g *ToolGuard) WrapEnhancedInvokableToolCall(ctx context.Context, endpoint adk.EnhancedInvokableToolCallEndpoint, tCtx *adk.ToolContext) (adk.EnhancedInvokableToolCallEndpoint, error) {
	return func(ctx context.Context, toolArgument *schema.ToolArgument, opts ...tool.Option) (*schema.ToolResult, error) {
		if err := g.check(ctx, tCtx); err != nil {
			g.deny(tCtx, err)
			return nil, err
		}
		return endpoint(ctx, toolArgument, opts...)
	}, nil
}

// WrapEnhancedStreamableToolCall 拦截增强流式工具。
func (g *ToolGuard) WrapEnhancedStreamableToolCall(ctx context.Context, endpoint adk.EnhancedStreamableToolCallEndpoint, tCtx *adk.ToolContext) (adk.EnhancedStreamableToolCallEndpoint, error) {
	return func(ctx context.Context, toolArgument *schema.ToolArgument, opts ...tool.Option) (*schema.StreamReader[*schema.ToolResult], error) {
		if err := g.check(ctx, tCtx); err != nil {
			g.deny(tCtx, err)
			return nil, err
		}
		return endpoint(ctx, toolArgument, opts...)
	}, nil
}

// deny 记录被拒绝的调用，便于安全审计。
func (g *ToolGuard) deny(tCtx *adk.ToolContext, err error) {
	name := ""
	if tCtx != nil {
		name = tCtx.Name
	}
	g.log.Warn("工具调用被拒绝",
		zap.String("tool", name),
		zap.Error(err),
	)
}
