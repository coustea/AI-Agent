package capability

import (
	"context"
	"testing"

	"github.com/cloudwego/eino/components/tool"
)

// TestRegistrySkipsNil 验证 nil 能力被自动跳过。
//
// 这是注册表的核心价值：调用方不需要到处写 nil 判断。
func TestRegistrySkipsNil(t *testing.T) {
	r := NewRegistry(nil, nil, nil)
	if r.Len() != 0 {
		t.Errorf("全为 nil 时应为空，实际 %d", r.Len())
	}
	if got := r.Tools(); len(got) != 0 {
		t.Errorf("Tools 应为空，实际 %d", len(got))
	}
}

// TestRegistryNilSafe 验证 nil 注册表安全。
func TestRegistryNilSafe(t *testing.T) {
	var r *Registry
	if r.Len() != 0 {
		t.Error("nil 注册表 Len 应为 0")
	}
	if len(r.Tools()) != 0 {
		t.Error("nil 注册表 Tools 应为空")
	}
	if len(r.Names()) != 0 {
		t.Error("nil 注册表 Names 应为空")
	}
}

// TestMemoryCapabilityDisabledWhenNil 验证未提供 recorder 时不注册记忆能力。
func TestMemoryCapabilityDisabledWhenNil(t *testing.T) {
	if got := Memory(nil); got != nil {
		t.Error("recorder 为 nil 时不应启用记忆能力")
	}

	r := NewRegistry(Memory(nil))
	if r.Len() != 0 {
		t.Errorf("应跳过未启用的能力，实际 %d", r.Len())
	}
}

// stubRecorder 满足 memory.Recorder。
type stubRecorder struct{}

func (stubRecorder) AppendPending(_ context.Context, _, _ string) error { return nil }

// TestMemoryCapabilityEnabled 验证提供了 recorder 就注册记忆能力。
func TestMemoryCapabilityEnabled(t *testing.T) {
	got := Memory(stubRecorder{})
	if got == nil {
		t.Fatal("recorder 非 nil 时应启用记忆能力")
	}
	var _ tool.BaseTool = got

	r := NewRegistry(got)
	if r.Len() != 1 {
		t.Errorf("应注册 1 个能力，实际 %d", r.Len())
	}
	names := r.Names()
	if len(names) != 1 || names[0] != "remember" {
		t.Errorf("能力名应为 remember，实际 %v", names)
	}
}
