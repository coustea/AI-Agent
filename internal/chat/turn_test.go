package chat

import (
	"context"
	"errors"
	"testing"
	"time"

	"mentorly/internal/infra"
)

// TestResolveOutcomeCompleted 验证正常完成时返回 completed。
func TestResolveOutcomeCompleted(t *testing.T) {
	status, content := resolveOutcome(nil, nil, context.Background())
	if status != StatusCompleted {
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
	if status != StatusCancelled {
		t.Errorf("status = %q, want cancelled", status)
	}
	if content == "" {
		t.Error("取消时也应写入占位说明")
	}
}

// TestResolveOutcomeCancelledKeepsPartial 验证取消时保留已生成的文本。
func TestResolveOutcomeCancelledKeepsPartial(t *testing.T) {
	res := &StreamResult{Answer: "已经生成的半截回答"}
	status, content := resolveOutcome(res, context.Canceled, context.Background())
	if status != StatusCancelled {
		t.Errorf("status = %q", status)
	}
	if content != "已经生成的半截回答" {
		t.Errorf("应保留半截文本，实际 %q", content)
	}
}

// TestResolveOutcomeFailed 验证其他错误按 failed 收口。
func TestResolveOutcomeFailed(t *testing.T) {
	status, _ := resolveOutcome(nil, errors.New("模型炸了"), context.Background())
	if status != StatusFailed {
		t.Errorf("status = %q, want failed", status)
	}
}

// TestResolveOutcomeCtxCancelledWithoutError 是关键回归测试：
// 客户端断开时 streamErr 可能为 nil，但 ctx 已取消，必须按 cancelled 收口，
// 否则会误记为 completed。
//
// 这个顺序错误在重构前真实存在：streamErr == nil 分支排在
// ctx 已取消判断之前，导致用户看到「回答完整」，实际只收到半截。
func TestResolveOutcomeCtxCancelledWithoutError(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	status, _ := resolveOutcome(nil, nil, ctx)
	if status != StatusCancelled {
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

// TestServiceDisabled 验证未配置模型时 Enabled 为 false。
func TestServiceDisabled(t *testing.T) {
	s := New(Deps{})
	if s.Enabled() {
		t.Error("未提供 runner 时不应启用")
	}
}

// TestServiceNilSafe 验证 nil 接收者安全。
func TestServiceNilSafe(t *testing.T) {
	var s *Service
	if s.Enabled() {
		t.Error("nil service 不应启用")
	}
	// Close 与 Begin 在 nil 上不应 panic。
	s.Close(time.Second)
	if _, err := s.Begin(context.Background(), "u", "s", "q"); !errors.Is(err, ErrUnavailable) {
		t.Errorf("nil service Begin 应返回 ErrUnavailable，实际 %v", err)
	}
}

// fakeLock 记录获取与释放次数。
type fakeLock struct {
	busy    bool
	release int
}

func (l *fakeLock) Acquire(_ context.Context, _ string, _ time.Duration) (func(), error) {
	if l.busy {
		return nil, infra.ErrLockBusy
	}
	return func() { l.release++ }, nil
}

// TestTurnCloseIsIdempotent 验证 Close 重复调用只释放一次锁。
//
// 这是 Begin/Close 取代 Prepare/Release 的核心收益：
// handler 可以无条件 defer，不必在每条错误路径手动释放。
func TestTurnCloseIsIdempotent(t *testing.T) {
	lock := &fakeLock{}
	turn := &Turn{release: func() { lock.release++ }}

	turn.Close()
	turn.Close()
	turn.Close()

	if lock.release != 1 {
		t.Errorf("Close 应只释放一次，实际 %d 次", lock.release)
	}
}

// TestTurnCloseNilSafe 验证 nil Turn 与 nil release 安全。
func TestTurnCloseNilSafe(t *testing.T) {
	var turn *Turn
	turn.Close() // 不应 panic

	(&Turn{}).Close() // release 为 nil 时也不应 panic
}

// TestEmptyQuestionRejected 验证空问题在未启用时先报不可用。
func TestEmptyQuestionRejected(t *testing.T) {
	s := New(Deps{})
	if _, err := s.Begin(context.Background(), "u1", "s1", "   "); !errors.Is(err, ErrUnavailable) {
		t.Fatalf("未启用时应返回 ErrUnavailable，实际 %v", err)
	}
}
