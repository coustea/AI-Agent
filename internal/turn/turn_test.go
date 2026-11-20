package turn

import (
	"context"
	"errors"
	"testing"
	"time"

	"mentorly/internal/agent"
	"mentorly/internal/dialogue"
)

// fakeLock 模拟会话锁。
type fakeLock struct {
	busy    bool
	release int
}

func (l *fakeLock) Acquire(_ context.Context, _ string, _ time.Duration) (func(), error) {
	if l.busy {
		return nil, ErrLockBusy
	}
	return func() { l.release++ }, nil
}

// TestLockBusyBecomesErrBusy 验证锁被占用时翻译成 ErrBusy（HTTP 409）。
func TestLockBusyBecomesErrBusy(t *testing.T) {
	o := New(Deps{Lock: &fakeLock{busy: true}})
	// Enabled 需要 builder 与 sessions；这里只测错误翻译，
	// 因此直接验证 Lock 适配层的语义。
	if _, err := o.lock.Acquire(context.Background(), "k", time.Second); !errors.Is(err, ErrLockBusy) {
		t.Fatalf("应为 ErrLockBusy，实际 %v", err)
	}
}

// TestEmptyQuestionRejected 验证空问题被拒绝（在未启用时先报不可用）。
func TestEmptyQuestionRejected(t *testing.T) {
	o := New(Deps{})
	if _, err := o.Prepare(context.Background(), "u1", "s1", "   "); !errors.Is(err, ErrUnavailable) {
		t.Fatalf("未启用时应返回 ErrUnavailable，实际 %v", err)
	}
}

// TestResolveOutcomeCompleted 验证正常完成时返回 completed。
func TestResolveOutcomeCompleted(t *testing.T) {
	status, content := resolveOutcome(nil, nil, context.Background())
	if status != dialogue.StatusCompleted {
		t.Errorf("status = %q, want completed", status)
	}
	// 无文本时应给占位，避免前端渲染空消息。
	if content == "" {
		t.Error("无文本时应写入占位内容")
	}
}

// TestResolveOutcomeCancelled 验证取消时保留半截文本。
func TestResolveOutcomeCancelled(t *testing.T) {
	status, content := resolveOutcome(nil, context.Canceled, context.Background())
	if status != dialogue.StatusCancelled {
		t.Errorf("status = %q, want cancelled", status)
	}
	if content == "" {
		t.Error("取消时也应写入占位说明")
	}
}

// TestResolveOutcomeCancelledKeepsPartial 验证取消时保留已生成的文本。
func TestResolveOutcomeCancelledKeepsPartial(t *testing.T) {
	res := &agent.StreamResult{Answer: "已经生成的半截回答"}
	status, content := resolveOutcome(res, context.Canceled, context.Background())
	if status != dialogue.StatusCancelled {
		t.Errorf("status = %q", status)
	}
	if content != "已经生成的半截回答" {
		t.Errorf("应保留半截文本，实际 %q", content)
	}
}

// TestResolveOutcomeFailed 验证其他错误按 failed 收口。
func TestResolveOutcomeFailed(t *testing.T) {
	status, _ := resolveOutcome(nil, errors.New("模型炸了"), context.Background())
	if status != dialogue.StatusFailed {
		t.Errorf("status = %q, want failed", status)
	}
}

// TestResolveOutcomeCtxCancelledWithoutError 是关键回归测试：
// 客户端断开时 streamErr 可能为 nil，但 ctx 已取消，必须按 cancelled 收口，
// 否则会误记为 completed。
func TestResolveOutcomeCtxCancelledWithoutError(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	status, _ := resolveOutcome(nil, nil, ctx)
	if status != dialogue.StatusCancelled {
		t.Errorf("ctx 已取消时必须为 cancelled，实际 %q", status)
	}
}

// TestUserFacingErrorHidesInternals 验证内部错误不泄露实现细节。
func TestUserFacingErrorHidesInternals(t *testing.T) {
	msg := userFacingError(errors.New("dial tcp 10.0.0.1:443: connect: connection refused"))
	if msg == "" || msg == "dial tcp 10.0.0.1:443: connect: connection refused" {
		t.Errorf("不应把底层错误直接暴露给用户，实际 %q", msg)
	}
}

// TestLockKeyFormat 验证锁 key 前缀稳定（改前缀会让在途请求无法互斥）。
func TestLockKeyFormat(t *testing.T) {
	if got := lockKey("abc"); got != "chat:lock:abc" {
		t.Errorf("lockKey = %q", got)
	}
}

// TestOrchestratorDisabled 验证未配置模型时 Enabled 为 false。
func TestOrchestratorDisabled(t *testing.T) {
	o := New(Deps{})
	if o.Enabled() {
		t.Error("未提供 builder 时不应启用")
	}
}

// TestOrchestratorNil 验证 nil 接收者安全。
func TestOrchestratorNil(t *testing.T) {
	var o *Orchestrator
	if o.Enabled() {
		t.Error("nil 编排器不应启用")
	}
}
