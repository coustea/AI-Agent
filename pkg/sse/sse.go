// Package sse 提供 Server-Sent Events 的帧定义与写入器。
//
// 帧类型与业务约定：
//   - delta  {text}              增量文本
//   - reset  {}                   工具调用前的过渡语作废，客户端应清空已渲染内容
//   - done   {message_id,status} 本轮结束
//   - error  {message}           错误
//
// 另外以 ": ping" 注释行做心跳保活，避免中间代理因空闲断开连接。
package sse

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

// 帧事件名
const (
	EventDelta = "delta"
	EventReset = "reset"
	EventDone  = "done"
	EventError = "error"
)

// Frame 是一个 SSE 帧。
// Data 会被 JSON 序列化；注释只会产生 ": xxx" 心跳行。
type Frame struct {
	Event string
	Data  any
	// Comment 非空时输出为注释行（心跳），忽略 Event/Data
	Comment string
}

// Delta 构造增量文本帧。
func Delta(text string) Frame {
	return Frame{Event: EventDelta, Data: map[string]string{"text": text}}
}

// Reset 构造「清空已渲染内容」帧。
func Reset() Frame {
	return Frame{Event: EventReset, Data: struct{}{}}
}

// Done 构造结束帧。
func Done(messageID uint64, status string) Frame {
	return Frame{Event: EventDone, Data: map[string]any{
		"message_id": messageID,
		"status":     status,
	}}
}

// Error 构造错误帧。
func Error(message string) Frame {
	return Frame{Event: EventError, Data: map[string]string{"message": message}}
}

// Ping 构造心跳帧。
func Ping() Frame {
	return Frame{Comment: "ping"}
}

// Writer 串行化地向 ResponseWriter 写帧，并内置心跳。
// 必须串行写入：多个 goroutine 并发写同一连接会产生交错帧。
type Writer struct {
	mu      sync.Mutex
	w       io.Writer
	flusher http.Flusher
	written bool
}

// NewWriter 写入 SSE 响应头并返回写入器。
// 调用方需保证此时尚未写入任何 body。
func NewWriter(w http.ResponseWriter) (*Writer, error) {
	h := w.Header()
	h.Set("Content-Type", "text/event-stream; charset=utf-8")
	h.Set("Cache-Control", "no-cache")
	h.Set("Connection", "keep-alive")
	// 关闭 Nginx 等反向代理的缓冲，否则流式内容会被攒着一次性下发。
	h.Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)

	flusher, ok := w.(http.Flusher)
	if !ok {
		return nil, fmt.Errorf("ResponseWriter 不支持 Flush，无法使用 SSE")
	}
	flusher.Flush()

	return &Writer{w: w, flusher: flusher}, nil
}

// Write 写入一个帧并立即 flush。
func (s *Writer) Write(f Frame) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	var buf []byte
	if f.Comment != "" {
		buf = fmt.Appendf(nil, ": %s\n\n", f.Comment)
	} else {
		payload, err := json.Marshal(f.Data)
		if err != nil {
			return fmt.Errorf("序列化 SSE 帧失败: %w", err)
		}
		buf = fmt.Appendf(nil, "event: %s\ndata: %s\n\n", f.Event, payload)
	}

	if _, err := s.w.Write(buf); err != nil {
		return err
	}
	s.written = true
	s.flusher.Flush()
	return nil
}

// Heartbeat 周期性发送心跳，直到 done 被关闭。
//
// 心跳写失败说明连接已断：此时通过 onBroken 通知调用方（可为 nil），
// 调用方应据此取消本轮生成，否则会白白继续产出并按 completed 落库。
func (s *Writer) Heartbeat(done <-chan struct{}, interval time.Duration, onBroken func()) {
	if interval <= 0 {
		interval = 15 * time.Second
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-done:
			return
		case <-ticker.C:
			if err := s.Write(Ping()); err != nil {
				if onBroken != nil {
					onBroken()
				}
				return
			}
		}
	}
}
