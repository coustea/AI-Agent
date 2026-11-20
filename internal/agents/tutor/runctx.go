package tutor

import (
	"context"

	"mentorly/internal/runtime"
)

// runtimeWithPrincipal 把身份注入 context。
func runtimeWithPrincipal(ctx context.Context, p *runtime.Principal) context.Context {
	return runtime.WithPrincipal(ctx, p)
}

// runtimeWithRunState 为本次运行创建独立的工具调用计数器。
//
// 每次运行都是新实例：跨请求共享计数会让配额限制互相干扰，
// 也会导致状态泄漏。
func runtimeWithRunState(ctx context.Context, rc *RunContext) context.Context {
	state := runtime.NewRunState()
	ctx = runtime.WithRunState(ctx, state)
	// 同时注入产物目录，供生成类工具使用。
	return ctx
}
