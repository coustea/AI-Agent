package sse

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// TestWriterFrameFormat 验证帧格式符合 SSE 规范。
func TestWriterFrameFormat(t *testing.T) {
	rec := httptest.NewRecorder()
	w, err := NewWriter(rec)
	if err != nil {
		t.Fatalf("NewWriter: %v", err)
	}

	if err := w.Write(Delta("你好")); err != nil {
		t.Fatalf("Write delta: %v", err)
	}
	if err := w.Write(Reset()); err != nil {
		t.Fatalf("Write reset: %v", err)
	}
	if err := w.Write(Done(42, "completed")); err != nil {
		t.Fatalf("Write done: %v", err)
	}

	body := rec.Body.String()

	// 每个帧以 "event: <name>\ndata: <json>\n\n" 形式出现
	for _, want := range []string{
		"event: delta",
		`"text":"你好"`,
		"event: reset",
		"event: done",
		`"message_id":42`,
		`"status":"completed"`,
	} {
		if !strings.Contains(body, want) {
			t.Errorf("响应体应包含 %q，实际:\n%s", want, body)
		}
	}

	// 帧之间用空行分隔
	if !strings.Contains(body, "\n\n") {
		t.Error("帧之间应有空行分隔")
	}
}

// TestWriterHeaders 验证 SSE 必需的响应头。
func TestWriterHeaders(t *testing.T) {
	rec := httptest.NewRecorder()
	if _, err := NewWriter(rec); err != nil {
		t.Fatalf("NewWriter: %v", err)
	}

	h := rec.Header()
	cases := map[string]string{
		"Content-Type":      "text/event-stream",
		"Cache-Control":     "no-cache",
		"X-Accel-Buffering": "no",
	}
	for k, want := range cases {
		got := h.Get(k)
		if k == "Content-Type" {
			if !strings.Contains(got, want) {
				t.Errorf("%s = %q, 应包含 %q", k, got, want)
			}
			continue
		}
		if got != want {
			t.Errorf("%s = %q, want %q", k, got, want)
		}
	}
}

// TestWriterPing 验证心跳是注释行。
func TestWriterPing(t *testing.T) {
	rec := httptest.NewRecorder()
	w, err := NewWriter(rec)
	if err != nil {
		t.Fatalf("NewWriter: %v", err)
	}

	if err := w.Write(Ping()); err != nil {
		t.Fatalf("Write ping: %v", err)
	}

	body := rec.Body.String()
	if !strings.HasPrefix(body, ": ping") {
		t.Errorf("心跳应为注释行，实际 %q", body)
	}
}

// TestHeartbeat 验证心跳按间隔重复发送，并在 done 关闭后退出。
func TestHeartbeat(t *testing.T) {
	rec := httptest.NewRecorder()
	w, err := NewWriter(rec)
	if err != nil {
		t.Fatalf("NewWriter: %v", err)
	}

	done := make(chan struct{})
	finished := make(chan struct{})

	// 用很短的间隔，保证测试快速完成
	go func() {
		w.Heartbeat(done, 20*time.Millisecond, nil)
		close(finished)
	}()

	time.Sleep(90 * time.Millisecond)
	close(done)

	select {
	case <-finished:
	case <-time.After(2 * time.Second):
		t.Fatal("心跳 goroutine 未退出")
	}

	body := rec.Body.String()
	if n := strings.Count(body, ": ping"); n < 3 {
		t.Errorf("应至少发送 3 次心跳，实际 %d 次", n)
	}
}

// TestErrorFrame 验证错误帧。
func TestErrorFrame(t *testing.T) {
	f := Error("生成失败")
	if f.Event != EventError {
		t.Errorf("事件名 = %q, want %q", f.Event, EventError)
	}

	rec := httptest.NewRecorder()
	w, _ := NewWriter(rec)
	_ = w.Write(f)

	if !strings.Contains(rec.Body.String(), "生成失败") {
		t.Error("错误帧应包含错误信息")
	}
}

// TestNewWriterRequiresFlusher 验证不支持 Flush 的 ResponseWriter 被拒绝。
func TestNewWriterRequiresFlusher(t *testing.T) {
	// noFlushWriter 故意不实现 http.Flusher
	if _, err := NewWriter(&noFlushWriter{h: http.Header{}}); err == nil {
		t.Error("不支持 Flush 时应报错")
	}
}

type noFlushWriter struct {
	h http.Header
}

func (n *noFlushWriter) Header() http.Header         { return n.h }
func (n *noFlushWriter) Write(p []byte) (int, error) { return len(p), nil }
func (n *noFlushWriter) WriteHeader(int)             {}

// brokenWriter 在写入若干次后开始报错，模拟客户端断开。
type brokenWriter struct {
	h      http.Header
	writes int
	failAt int
}

func (b *brokenWriter) Header() http.Header { return b.h }
func (b *brokenWriter) WriteHeader(int)     {}
func (b *brokenWriter) Write(p []byte) (int, error) {
	b.writes++
	if b.writes > b.failAt {
		return 0, errors.New("broken pipe")
	}
	return len(p), nil
}
func (b *brokenWriter) Flush() {}

// TestHeartbeatNotifiesBroken 验证心跳写失败时回调 onBroken，
// 让上层能取消本轮生成（否则会继续产出并按 completed 落库）。
func TestHeartbeatNotifiesBroken(t *testing.T) {
	bw := &brokenWriter{h: http.Header{}, failAt: 0}
	w, err := NewWriter(bw)
	if err != nil {
		t.Fatalf("NewWriter: %v", err)
	}

	broken := make(chan struct{})
	done := make(chan struct{})
	finished := make(chan struct{})

	go func() {
		w.Heartbeat(done, 10*time.Millisecond, func() {
			select {
			case <-broken:
			default:
				close(broken)
			}
		})
		close(finished)
	}()

	select {
	case <-broken:
		// 符合预期
	case <-time.After(2 * time.Second):
		t.Fatal("心跳失败应触发 onBroken 回调")
	}

	close(done)
	select {
	case <-finished:
	case <-time.After(2 * time.Second):
		t.Fatal("心跳 goroutine 未退出")
	}
}
