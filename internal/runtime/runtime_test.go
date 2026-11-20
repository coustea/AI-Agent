package runtime

import (
	"context"
	"errors"
	"testing"
	"time"
)

// TestPrincipalRoundTrip 身份必须能在 context 中往返。
func TestPrincipalRoundTrip(t *testing.T) {
	p := &Principal{UserID: "u1", ConversationID: "c1", Workspace: "/tmp/ws"}

	ctx := WithPrincipal(context.Background(), p)
	got, ok := PrincipalFrom(ctx)
	if !ok {
		t.Fatal("读取失败")
	}
	if got.UserID != "u1" || got.ConversationID != "c1" {
		t.Errorf("身份 = %+v", got)
	}
}

// TestPrincipalFromMissing 没有身份时必须返回 false。
//
// 这是用户隔离的根基：Tool 靠这个判断拒绝执行，
// 一旦这里误判为 true，所有跨用户校验都会失效。
func TestPrincipalFromMissing(t *testing.T) {
	if _, ok := PrincipalFrom(context.Background()); ok {
		t.Error("空 context 不应有身份")
	}

	// 空 UserID 也算无效
	ctx := WithPrincipal(context.Background(), &Principal{ConversationID: "c1"})
	if _, ok := PrincipalFrom(ctx); ok {
		t.Error("空 UserID 不应视为有效身份")
	}

	// nil 指针
	ctx = WithPrincipal(context.Background(), nil)
	if _, ok := PrincipalFrom(ctx); ok {
		t.Error("nil 身份不应有效")
	}
}

// TestMustPrincipal 缺失时返回统一错误。
func TestMustPrincipal(t *testing.T) {
	if _, err := MustPrincipal(context.Background()); !errors.Is(err, ErrNoPrincipal) {
		t.Errorf("错误 = %v, 期望 ErrNoPrincipal", err)
	}

	ctx := WithPrincipal(context.Background(), &Principal{UserID: "u1"})
	if _, err := MustPrincipal(ctx); err != nil {
		t.Errorf("意外错误: %v", err)
	}
}

// TestCountToolCall 计数器必须按运行隔离。
//
// 若跨请求共享，配额限制会互相干扰：A 用户调用 3 次后，
// B 用户可能一上来就被拒绝。
func TestCountToolCall(t *testing.T) {
	// 没有运行状态时返回 0，调用方据此放行
	if got := CountToolCall(context.Background(), "any"); got != 0 {
		t.Errorf("无状态时计数 = %d, 期望 0", got)
	}

	ctx := WithRunState(context.Background(), NewRunState())

	for i := 0; i < 3; i++ {
		if got := CountToolCall(ctx, "gen"); got != i {
			t.Errorf("第 %d 次调用返回 %d", i+1, got)
		}
	}

	// 不同工具独立计数
	if got := CountToolCall(ctx, "other"); got != 0 {
		t.Errorf("其他工具计数 = %d, 期望 0", got)
	}

	// 新运行状态从 0 开始
	ctx2 := WithRunState(context.Background(), NewRunState())
	if got := CountToolCall(ctx2, "gen"); got != 0 {
		t.Errorf("新状态计数 = %d, 期望 0", got)
	}
}

// TestRunStateConcurrent 并发调用计数不能丢失。
func TestRunStateConcurrent(t *testing.T) {
	ctx := WithRunState(context.Background(), NewRunState())
	const n = 100

	done := make(chan struct{})
	for i := 0; i < n; i++ {
		go func() {
			CountToolCall(ctx, "tool")
			done <- struct{}{}
		}()
	}
	for i := 0; i < n; i++ {
		<-done
	}

	// 第 n+1 次调用应返回 n（前面已调用 n 次）
	if got := CountToolCall(ctx, "tool"); got != n {
		t.Errorf("并发计数 = %d, 期望 %d", got, n)
	}
}

// TestNormalizeBaseURL 校验 base_url 归一化。
func TestNormalizeBaseURL(t *testing.T) {
	ok := map[string]string{
		"https://api.example.com/v1":   "https://api.example.com/v1",
		"https://api.example.com/v1/":  "https://api.example.com/v1",
		"http://127.0.0.1:8080":        "http://127.0.0.1:8080",
		" https://api.example.com/v1 ": "https://api.example.com/v1",
	}
	for in, want := range ok {
		got, err := NormalizeBaseURL(in)
		if err != nil {
			t.Errorf("NormalizeBaseURL(%q) 报错: %v", in, err)
			continue
		}
		if got != want {
			t.Errorf("NormalizeBaseURL(%q) = %q, 期望 %q", in, got, want)
		}
	}

	bad := []string{
		"",
		"api.example.com/v1",    // 缺 scheme
		"ftp://api.example.com", // 协议不支持
		"https://api.example.com/v1/chat/completions", // eino 会重复拼接
	}
	for _, in := range bad {
		if _, err := NormalizeBaseURL(in); err == nil {
			t.Errorf("NormalizeBaseURL(%q) 应报错", in)
		}
	}
}

// TestJobRunnerLifecycle 任务从 queued 走到 completed。
func TestJobRunnerLifecycle(t *testing.T) {
	r := NewJobRunner(1, 10*time.Second, nil)
	defer r.Close(2 * time.Second)

	started := make(chan struct{})
	job, err := r.Submit("test", "job1", func(ctx context.Context, report func(int, string)) error {
		close(started)
		report(50, "一半")
		return nil
	})
	if err != nil {
		t.Fatalf("提交失败: %v", err)
	}
	if job.Status != JobQueued {
		t.Errorf("初始状态 = %q, 期望 queued", job.Status)
	}

	<-started

	got, err := r.Wait(context.Background(), "job1")
	if err != nil {
		t.Fatalf("等待失败: %v", err)
	}
	if got.Status != JobCompleted {
		t.Errorf("终态 = %q, 期望 completed", got.Status)
	}
}

// TestJobRunnerFailure 执行体返回错误时任务失败并记录原因。
func TestJobRunnerFailure(t *testing.T) {
	r := NewJobRunner(1, 10*time.Second, nil)
	defer r.Close(2 * time.Second)

	if _, err := r.Submit("test", "fail1", func(ctx context.Context, report func(int, string)) error {
		return errors.New("渲染失败")
	}); err != nil {
		t.Fatalf("提交失败: %v", err)
	}

	got, err := r.Wait(context.Background(), "fail1")
	if err != nil {
		t.Fatalf("等待失败: %v", err)
	}
	if got.Status != JobFailed {
		t.Errorf("终态 = %q, 期望 failed", got.Status)
	}
	if got.Error != "渲染失败" {
		t.Errorf("错误 = %q", got.Error)
	}
}

// TestJobRunnerDuplicate 重复 ID 必须被拒绝。
func TestJobRunnerDuplicate(t *testing.T) {
	r := NewJobRunner(1, 10*time.Second, nil)
	defer r.Close(2 * time.Second)

	block := make(chan struct{})
	if _, err := r.Submit("test", "dup", func(ctx context.Context, report func(int, string)) error {
		<-block
		return nil
	}); err != nil {
		t.Fatalf("首次提交失败: %v", err)
	}
	defer close(block)

	if _, err := r.Submit("test", "dup", func(ctx context.Context, report func(int, string)) error {
		return nil
	}); err == nil {
		t.Error("重复 ID 应被拒绝")
	}
}

// TestJobRunnerGet 未知任务返回 false。
func TestJobRunnerGet(t *testing.T) {
	r := NewJobRunner(1, time.Second, nil)
	defer r.Close(time.Second)

	if _, ok := r.Get("nope"); ok {
		t.Error("未知任务不应存在")
	}
	if _, err := r.Wait(context.Background(), "nope"); !errors.Is(err, ErrJobNotFound) {
		t.Errorf("错误 = %v, 期望 ErrJobNotFound", err)
	}
}

// TestJobRunnerPanicRecovery 执行体 panic 不能拖垮 worker。
func TestJobRunnerPanicRecovery(t *testing.T) {
	r := NewJobRunner(1, 5*time.Second, nil)
	defer r.Close(2 * time.Second)

	if _, err := r.Submit("test", "panic1", func(ctx context.Context, report func(int, string)) error {
		panic("boom")
	}); err != nil {
		t.Fatalf("提交失败: %v", err)
	}

	got, err := r.Wait(context.Background(), "panic1")
	if err != nil {
		t.Fatalf("等待失败: %v", err)
	}
	if got.Status != JobFailed {
		t.Errorf("panic 后状态 = %q, 期望 failed", got.Status)
	}

	// worker 仍能处理后续任务
	if _, err := r.Submit("test", "after", func(ctx context.Context, report func(int, string)) error {
		return nil
	}); err != nil {
		t.Fatalf("panic 后提交失败: %v", err)
	}
	got, err = r.Wait(context.Background(), "after")
	if err != nil {
		t.Fatalf("等待失败: %v", err)
	}
	if got.Status != JobCompleted {
		t.Errorf("后续任务状态 = %q", got.Status)
	}
}
