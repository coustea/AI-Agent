package llm

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// writeSSE 按 SSE 帧格式写入若干 data 载荷并立即刷新。
func writeSSE(t *testing.T, w http.ResponseWriter, payloads ...string) {
	t.Helper()

	w.Header().Set("Content-Type", "text/event-stream")
	flusher, _ := w.(http.Flusher)
	for _, p := range payloads {
		if _, err := io.WriteString(w, "data: "+p+"\n\n"); err != nil {
			return
		}
		if flusher != nil {
			flusher.Flush()
		}
	}
}

// 不变量 1/3：终块恰好一次、位于最后，且携带完整用量
func TestStream_TerminalIsLastWithUsage(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		writeSSE(t, w,
			`{"choices":[{"delta":{"content":"你"}}]}`,
			`{"choices":[{"delta":{"content":"好"}}]}`,
			`{"choices":[],"usage":{"prompt_tokens":3,"completion_tokens":4,"total_tokens":7}}`,
			`{"choices":[{"delta":{},"finish_reason":"stop"}]}`,
			sseDonePayload,
		)
	}))
	defer srv.Close()

	stream, err := newTestClient(t, srv.URL).ChatStream(t.Context(), Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var terminals int
	var last Chunk
	var text strings.Builder
	for chunk := range stream {
		if chunk.Terminal() {
			terminals++
		}
		last = chunk
		text.WriteString(chunk.Delta)
	}

	if terminals != 1 {
		t.Errorf("终块必须恰好一次，实际 %d 次", terminals)
	}
	if !last.Terminal() {
		t.Fatalf("最后一个元素必须是终块，实际 %+v", last)
	}
	if last.Finish != StopEnd || last.Err != nil {
		t.Errorf("期望 StopEnd 且无错误，实际 finish=%s err=%v", last.Finish, last.Err)
	}
	if last.Usage.TotalTokens != 7 {
		t.Errorf("终块应携带用量 7，实际 %d", last.Usage.TotalTokens)
	}
	if text.String() != "你好" {
		t.Errorf("增量拼接错误: %q", text.String())
	}
}

// 不变量 2：上游未给收尾信号就断开 → 截断错误，绝不当成正常完成
func TestStream_TruncatedWithoutFinish(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		writeSSE(t, w, `{"choices":[{"delta":{"content":"半截"}}]}`)
		// 直接返回：既无 [DONE] 也无 finish_reason
	}))
	defer srv.Close()

	stream, err := newTestClient(t, srv.URL).ChatStream(t.Context(), Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, terminal := collect(t, stream)
	if terminal.Finish != StopTruncated {
		t.Errorf("期望 StopTruncated，实际 %s", terminal.Finish)
	}
	if !errors.Is(terminal.Err, ErrStreamTruncated) {
		t.Errorf("期望 ErrStreamTruncated，实际 %v", terminal.Err)
	}
}

// 回归：末行没有换行符时，[DONE] 不能被 ReadString 的 io.EOF 吞掉
func TestStream_DoneWithoutTrailingNewline(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"ok\"}}]}\n\n")
		_, _ = io.WriteString(w, "data: "+sseDonePayload)
	}))
	defer srv.Close()

	stream, err := newTestClient(t, srv.URL).ChatStream(t.Context(), Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	deltas, terminal := collect(t, stream)
	if terminal.Finish != StopEnd || terminal.Err != nil {
		t.Fatalf("期望正常结束，实际 finish=%s err=%v", terminal.Finish, terminal.Err)
	}
	if strings.Join(deltas, "") != "ok" {
		t.Errorf("期望 ok，实际 %v", deltas)
	}
}

// 不变量 2：取消必须表达为 canceled + 非 nil 错误，不能被伪装成完成
func TestStream_CancelYieldsCanceled(t *testing.T) {
	release := make(chan struct{})
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		writeSSE(t, w, `{"choices":[{"delta":{"content":"hi"}}]}`)
		select {
		case <-release:
		case <-r.Context().Done():
		}
	}))
	defer srv.Close()
	defer close(release)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stream, err := newTestClient(t, srv.URL).ChatStream(ctx, Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var terminal Chunk
	for chunk := range stream {
		if chunk.Terminal() {
			terminal = chunk
			continue
		}
		if chunk.Delta == "hi" {
			cancel()
		}
	}

	if terminal.Finish != StopCanceled {
		t.Fatalf("期望 StopCanceled，实际 %s", terminal.Finish)
	}
	if !errors.Is(terminal.Err, context.Canceled) {
		t.Errorf("期望 context.Canceled，实际 %v", terminal.Err)
	}
	if terminal.Err == nil {
		t.Errorf("取消必须携带非 nil 错误")
	}
}

// 分片工具调用：按 index 归并、跨 chunk 拼接、按 index 升序还原
func TestStream_ToolCallsAssembled(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		writeSSE(t, w,
			`{"choices":[{"delta":{"tool_calls":[{"index":1,"id":"call_b","function":{"name":"beta","arguments":"{}"}}]}}]}`,
			`{"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_a","function":{"name":"al","arguments":"{\"x\""}}]}}]}`,
			`{"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":":1}"}}]}}]}`,
			`{"choices":[{"delta":{},"finish_reason":"tool_calls"}]}`,
			sseDonePayload,
		)
	}))
	defer srv.Close()

	stream, err := newTestClient(t, srv.URL).ChatStream(t.Context(), Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, terminal := collect(t, stream)
	if terminal.Finish != StopToolCalls {
		t.Fatalf("期望 StopToolCalls，实际 %s", terminal.Finish)
	}
	if len(terminal.ToolCalls) != 2 {
		t.Fatalf("期望 2 个工具调用，实际 %d", len(terminal.ToolCalls))
	}

	first, second := terminal.ToolCalls[0], terminal.ToolCalls[1]
	if first.ID != "call_a" || first.Name != "al" || first.Arguments != `{"x":1}` {
		t.Errorf("index 0 还原错误: %+v", first)
	}
	if second.ID != "call_b" || second.Name != "beta" {
		t.Errorf("index 1 还原错误: %+v", second)
	}
}

// 流中的错误信封必须显式失败，不能被当作空 chunk 跳过
func TestStream_ErrorEnvelopeMidStream(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		writeSSE(t, w,
			`{"choices":[{"delta":{"content":"部分"}}]}`,
			`{"error":{"message":"quota exceeded"}}`,
		)
	}))
	defer srv.Close()

	stream, err := newTestClient(t, srv.URL).ChatStream(t.Context(), Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, terminal := collect(t, stream)
	if terminal.Finish != StopFailed {
		t.Errorf("期望 StopFailed，实际 %s", terminal.Finish)
	}
	if terminal.Err == nil || !strings.Contains(terminal.Err.Error(), "quota exceeded") {
		t.Errorf("错误应带出上游 message，实际 %v", terminal.Err)
	}
}

// 非 data 行（注释、event、空行）必须被忽略，不影响解析
func TestStream_IgnoresNonDataLines(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, ": keep-alive\n\n")
		_, _ = io.WriteString(w, "event: message\n")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"x\"}}]}\n\n")
		_, _ = io.WriteString(w, "data: "+sseDonePayload+"\n\n")
	}))
	defer srv.Close()

	stream, err := newTestClient(t, srv.URL).ChatStream(t.Context(), Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	deltas, terminal := collect(t, stream)
	if terminal.Finish != StopEnd || terminal.Err != nil {
		t.Fatalf("期望正常结束，实际 finish=%s err=%v", terminal.Finish, terminal.Err)
	}
	if strings.Join(deltas, "") != "x" {
		t.Errorf("期望 x，实际 %v", deltas)
	}
}
