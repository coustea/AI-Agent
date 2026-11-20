package middleware

import (
	"context"
	"errors"
	"testing"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"

	"mentorly/internal/runtime"
)

// TestCheckRequiresPrincipal 需要身份的工具在没有 Principal 时必须被拒。
//
// 这是用户隔离的核心防线：一旦这里放行，
// 记忆、附件、产物就可能被跨用户访问。
func TestCheckRequiresPrincipal(t *testing.T) {
	g := NewToolGuard(nil)

	for name := range requiresPrincipal {
		err := g.check(context.Background(), &adk.ToolContext{Name: name})
		if !errors.Is(err, ErrToolDenied) {
			t.Errorf("工具 %q 无身份时应被拒，实际 err=%v", name, err)
		}
	}

	// 有身份时应放行
	ctx := runtime.WithPrincipal(context.Background(), &runtime.Principal{UserID: "u1"})
	ctx = runtime.WithRunState(ctx, runtime.NewRunState())
	for name := range requiresPrincipal {
		if err := g.check(ctx, &adk.ToolContext{Name: name}); err != nil {
			t.Errorf("工具 %q 有身份时应放行，实际 err=%v", name, err)
		}
	}
}

// TestCheckDoesNotRequirePrincipal 不需要身份的工具不受此限制。
func TestCheckDoesNotRequirePrincipal(t *testing.T) {
	g := NewToolGuard(nil)

	// web_search 不访问用户数据，无需身份
	if err := g.check(context.Background(), &adk.ToolContext{Name: "web_search"}); err != nil {
		t.Errorf("web_search 不应要求身份: %v", err)
	}
}

// TestCheckCallBudget 配额限制必须生效。
func TestCheckCallBudget(t *testing.T) {
	g := NewToolGuard(nil)

	ctx := runtime.WithPrincipal(context.Background(), &runtime.Principal{UserID: "u1"})
	ctx = runtime.WithRunState(ctx, runtime.NewRunState())

	name := "generate_explainer_video"
	limit := callBudget[name]

	// 前 limit 次应通过
	for i := 0; i < limit; i++ {
		if err := g.check(ctx, &adk.ToolContext{Name: name}); err != nil {
			t.Fatalf("第 %d 次调用被误拒: %v", i+1, err)
		}
	}

	// 超过后应被拒
	if err := g.check(ctx, &adk.ToolContext{Name: name}); !errors.Is(err, ErrToolDenied) {
		t.Errorf("超过配额应被拒，实际 err=%v", err)
	}
}

// TestCheckNilToolContext nil 上下文不应 panic。
func TestCheckNilToolContext(t *testing.T) {
	g := NewToolGuard(nil)
	if err := g.check(context.Background(), nil); err != nil {
		t.Errorf("nil ToolContext 应放行: %v", err)
	}
}

// TestWrapInvokableToolCall 同步工具包装必须执行校验。
func TestWrapInvokableToolCall(t *testing.T) {
	g := NewToolGuard(nil)

	called := false
	endpoint := func(ctx context.Context, args string, opts ...tool.Option) (string, error) {
		called = true
		return "ok", nil
	}

	// 无身份：应被拒且不执行原 endpoint
	wrapped, err := g.WrapInvokableToolCall(context.Background(), endpoint, &adk.ToolContext{Name: "memory_search"})
	if err != nil {
		t.Fatalf("包装失败: %v", err)
	}
	if _, err := wrapped(context.Background(), "{}"); !errors.Is(err, ErrToolDenied) {
		t.Errorf("应被拒，实际 err=%v", err)
	}
	if called {
		t.Error("被拒时不应执行原 endpoint")
	}

	// 有身份：应执行
	ctx := runtime.WithPrincipal(context.Background(), &runtime.Principal{UserID: "u1"})
	ctx = runtime.WithRunState(ctx, runtime.NewRunState())
	out, err := wrapped(ctx, "{}")
	if err != nil {
		t.Fatalf("有身份时应执行: %v", err)
	}
	if out != "ok" || !called {
		t.Error("原 endpoint 未被执行")
	}
}

// TestWrapStreamableToolCall 流式工具包装必须执行校验。
//
// 只包装 Invokable 却漏掉 Streamable 是典型的安全假象：
// 框架按工具实际实现的接口分发，漏掉的类型会完全绕过校验。
func TestWrapStreamableToolCall(t *testing.T) {
	g := NewToolGuard(nil)

	called := false
	endpoint := func(ctx context.Context, args string, opts ...tool.Option) (*schema.StreamReader[string], error) {
		called = true
		return nil, nil
	}

	wrapped, err := g.WrapStreamableToolCall(context.Background(), endpoint, &adk.ToolContext{Name: "generate_diagram"})
	if err != nil {
		t.Fatalf("包装失败: %v", err)
	}

	if _, err := wrapped(context.Background(), "{}"); !errors.Is(err, ErrToolDenied) {
		t.Errorf("应被拒，实际 err=%v", err)
	}
	if called {
		t.Error("被拒时不应执行原 endpoint")
	}

	ctx := runtime.WithPrincipal(context.Background(), &runtime.Principal{UserID: "u1"})
	ctx = runtime.WithRunState(ctx, runtime.NewRunState())
	if _, err := wrapped(ctx, "{}"); err != nil {
		t.Fatalf("有身份时应执行: %v", err)
	}
	if !called {
		t.Error("原 endpoint 未被执行")
	}
}

// TestWrapEnhancedInvokableToolCall 增强同步工具包装必须执行校验。
func TestWrapEnhancedInvokableToolCall(t *testing.T) {
	g := NewToolGuard(nil)

	called := false
	endpoint := func(ctx context.Context, arg *schema.ToolArgument, opts ...tool.Option) (*schema.ToolResult, error) {
		called = true
		return &schema.ToolResult{}, nil
	}

	wrapped, err := g.WrapEnhancedInvokableToolCall(context.Background(), endpoint, &adk.ToolContext{Name: "memory_save"})
	if err != nil {
		t.Fatalf("包装失败: %v", err)
	}

	if _, err := wrapped(context.Background(), &schema.ToolArgument{}); !errors.Is(err, ErrToolDenied) {
		t.Errorf("应被拒，实际 err=%v", err)
	}
	if called {
		t.Error("被拒时不应执行原 endpoint")
	}

	ctx := runtime.WithPrincipal(context.Background(), &runtime.Principal{UserID: "u1"})
	ctx = runtime.WithRunState(ctx, runtime.NewRunState())
	if _, err := wrapped(ctx, &schema.ToolArgument{}); err != nil {
		t.Fatalf("有身份时应执行: %v", err)
	}
	if !called {
		t.Error("原 endpoint 未被执行")
	}
}

// TestWrapEnhancedStreamableToolCall 增强流式工具包装必须执行校验。
func TestWrapEnhancedStreamableToolCall(t *testing.T) {
	g := NewToolGuard(nil)

	called := false
	endpoint := func(ctx context.Context, arg *schema.ToolArgument, opts ...tool.Option) (*schema.StreamReader[*schema.ToolResult], error) {
		called = true
		return nil, nil
	}

	wrapped, err := g.WrapEnhancedStreamableToolCall(context.Background(), endpoint, &adk.ToolContext{Name: "read_attachment"})
	if err != nil {
		t.Fatalf("包装失败: %v", err)
	}

	if _, err := wrapped(context.Background(), &schema.ToolArgument{}); !errors.Is(err, ErrToolDenied) {
		t.Errorf("应被拒，实际 err=%v", err)
	}
	if called {
		t.Error("被拒时不应执行原 endpoint")
	}

	ctx := runtime.WithPrincipal(context.Background(), &runtime.Principal{UserID: "u1"})
	ctx = runtime.WithRunState(ctx, runtime.NewRunState())
	if _, err := wrapped(ctx, &schema.ToolArgument{}); err != nil {
		t.Fatalf("有身份时应执行: %v", err)
	}
	if !called {
		t.Error("原 endpoint 未被执行")
	}
}

// TestAllWrapMethodsImplemented 确保四种工具类型都被覆盖。
//
// 这个测试的价值在于：如果有人新增了工具类型或漏实现某个 Wrap，
// 这里会直接暴露，而不是等到线上发现某个类型的工具完全不受保护。
func TestAllWrapMethodsImplemented(t *testing.T) {
	g := NewToolGuard(nil)

	// 四个 Wrap 方法都必须返回非 nil 包装函数
	invokable, err := g.WrapInvokableToolCall(context.Background(),
		func(context.Context, string, ...tool.Option) (string, error) { return "", nil },
		&adk.ToolContext{Name: "x"})
	if err != nil || invokable == nil {
		t.Error("WrapInvokableToolCall 未实现")
	}

	streamable, err := g.WrapStreamableToolCall(context.Background(),
		func(context.Context, string, ...tool.Option) (*schema.StreamReader[string], error) { return nil, nil },
		&adk.ToolContext{Name: "x"})
	if err != nil || streamable == nil {
		t.Error("WrapStreamableToolCall 未实现")
	}

	enhInv, err := g.WrapEnhancedInvokableToolCall(context.Background(),
		func(context.Context, *schema.ToolArgument, ...tool.Option) (*schema.ToolResult, error) {
			return nil, nil
		},
		&adk.ToolContext{Name: "x"})
	if err != nil || enhInv == nil {
		t.Error("WrapEnhancedInvokableToolCall 未实现")
	}

	enhStr, err := g.WrapEnhancedStreamableToolCall(context.Background(),
		func(context.Context, *schema.ToolArgument, ...tool.Option) (*schema.StreamReader[*schema.ToolResult], error) {
			return nil, nil
		},
		&adk.ToolContext{Name: "x"})
	if err != nil || enhStr == nil {
		t.Error("WrapEnhancedStreamableToolCall 未实现")
	}
}

// TestProtectedToolsCoverage 校验受保护工具清单覆盖了全部有用户数据的工具。
func TestProtectedToolsCoverage(t *testing.T) {
	// 这些工具都会读写用户数据，必须出现在 requiresPrincipal 中。
	mustProtect := []string{
		"memory_search", "memory_save", "memory_delete",
		"read_attachment", "list_attachments",
		"generate_diagram", "generate_presentation", "generate_explainer_video",
		"get_artifact_status",
	}

	for _, name := range mustProtect {
		if !requiresPrincipal[name] {
			t.Errorf("工具 %q 未加入受保护清单", name)
		}
	}
}
