package chat

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/gin-gonic/gin"

	"mentorly/internal/response"
)

// Handler 是 chat 模块的 HTTP 入口。
type Handler struct {
	svc *Service
	// heartbeat SSE 心跳间隔
	heartbeat time.Duration
	// userID 从请求上下文取当前登录用户。
	// 由 api 层注入，使本模块不依赖 auth 包，避免两个上下文互相 import。
	userID func(*gin.Context) string
}

// HandlerDeps 是 handler 的装配参数。
type HandlerDeps struct {
	Service   *Service
	Heartbeat time.Duration
	// UserID 从 gin 上下文取当前用户 id，必须非空。
	UserID func(*gin.Context) string
}

// NewHandler 构造 handler。
func NewHandler(d HandlerDeps) *Handler {
	hb := d.Heartbeat
	if hb <= 0 {
		hb = 15 * time.Second
	}
	return &Handler{svc: d.Service, heartbeat: hb, userID: d.UserID}
}

// currentUserID 取当前用户，缺失时返回空串（由中间件保证不会发生）。
func (h *Handler) currentUserID(c *gin.Context) string {
	if h.userID == nil {
		return ""
	}
	return h.userID(c)
}

// CreateSession 创建会话
func (h *Handler) CreateSession(c *gin.Context) {
	// 允许空 body：等价于用默认标题创建会话。
	// 只有在确实带了 body 且解析失败时才报 400。
	var req CreateSessionReq
	if c.Request.ContentLength != 0 {
		if err := c.ShouldBindJSON(&req); err != nil {
			response.BadRequest(c, err.Error())
			return
		}
	}

	sess, err := h.svc.CreateSession(c.Request.Context(), h.currentUserID(c), req.Title)
	if err != nil {
		response.ServerError(c, "创建会话失败")
		return
	}
	response.OK(c, toSessionResp(sess))
}

// ListSessions 会话列表
func (h *Handler) ListSessions(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))

	list, err := h.svc.ListSessions(c.Request.Context(), h.currentUserID(c), limit)
	if err != nil {
		response.ServerError(c, "查询会话列表失败")
		return
	}
	response.OK(c, toSessionList(list))
}

// RenameSession 重命名会话
func (h *Handler) RenameSession(c *gin.Context) {
	var req RenameSessionReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	if err := h.svc.RenameSession(c.Request.Context(), h.currentUserID(c), c.Param("id"), req.Title); err != nil {
		if errors.Is(err, ErrSessionNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		response.ServerError(c, "重命名会话失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}

// DeleteSession 软删除会话
func (h *Handler) DeleteSession(c *gin.Context) {
	if err := h.svc.DeleteSession(c.Request.Context(), h.currentUserID(c), c.Param("id")); err != nil {
		if errors.Is(err, ErrSessionNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		response.ServerError(c, "删除会话失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}

// ListMessages 游标分页查询历史
func (h *Handler) ListMessages(c *gin.Context) {
	beforeID, _ := strconv.ParseUint(c.DefaultQuery("before_id", "0"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))

	views, err := h.svc.Messages(c.Request.Context(), h.currentUserID(c), c.Param("id"), beforeID, limit)
	if err != nil {
		if errors.Is(err, ErrSessionNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		response.ServerError(c, "查询消息失败")
		return
	}
	response.OK(c, toMessageViews(views))
}

// SendMessage 发送消息，返回 SSE 流。
//
// 时序关键点：Begin（校验 + 加锁 + 落库 user 消息）必须在写出
// SSE 响应头之前完成——404/409/400 需要标准 JSON 状态码。
// 一旦校验通过，立即切换 event-stream 并启动心跳，
// 随后的上下文压缩（可能耗时数秒）由心跳帧保住连接。
func (h *Handler) SendMessage(c *gin.Context) {
	var req SendMessageReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	t, err := h.svc.Begin(c.Request.Context(), h.currentUserID(c), c.Param("id"), req.Content)
	if err != nil {
		switch {
		case errors.Is(err, ErrUnavailable):
			response.Unavailable(c, "对话能力未启用（未配置 llm.api_key）")
		case errors.Is(err, ErrSessionNotFound):
			response.NotFound(c, "会话不存在")
		case errors.Is(err, ErrBusy):
			response.Fail(c, http.StatusConflict, response.CodeConflict, ErrBusy.Error())
		case errors.Is(err, ErrEmptyQuestion):
			response.BadRequest(c, ErrEmptyQuestion.Error())
		default:
			response.ServerError(c, "发送消息失败")
		}
		return
	}
	// 锁随 Turn 生命周期，defer 兜住所有错误路径。
	defer t.Close()

	// 全局 WriteTimeout 对 SSE 太短：取消本请求的写超时。
	rc := http.NewResponseController(c.Writer)
	_ = rc.SetWriteDeadline(time.Time{})

	sw, err := newSSEWriter(c.Writer)
	if err != nil {
		return
	}

	// 关键：不能只依赖 c.Request.Context()。
	// net/http 在客户端断开时并不保证立刻取消 Request.Context（尤其当
	// 服务端正在写数据、尚未触及读方向时），而我们真正的断连信号是「写失败」。
	// 因此派生一个可主动取消的 ctx，写失败时立即取消，
	// 让编排层把本轮按 cancelled 收口，而不是继续生成并落库成 completed。
	runCtx, cancelRun := context.WithCancel(c.Request.Context())
	defer cancelRun()

	done := make(chan struct{})
	defer close(done)

	go sw.heartbeat(done, h.heartbeat, cancelRun)

	res := t.Run(runCtx, func(ch Chunk) error {
		if ch.Reset {
			return sw.reset()
		}
		if ch.Text != "" {
			if err := sw.delta(ch.Text); err != nil {
				return err
			}
		}
		return nil
	})

	// 客户端已断开时继续写只会报错，直接返回。
	if runCtx.Err() != nil {
		return
	}

	// 失败轮次补一个错误帧，让前端能展示原因而不是空消息。
	if res.Status == StatusFailed {
		_ = sw.error("生成失败，请稍后重试")
	}
	_ = sw.done(res.MessageID, res.Status)
}

// ---------- SSE writer ----------
//
// 帧契约（与前端约定，变更需同步）：
//
//	delta  {"text": "..."}      增量文本
//	reset  {}                   清空已渲染内容（工具调用前的过渡语作废）
//	done   {"message_id":..., "status":"completed|failed|cancelled"}
//	error  {"message": "..."}
//	: ping                      心跳注释行
type sseWriter struct {
	w  io.Writer
	fl http.Flusher
	mu sync.Mutex
}

// newSSEWriter 写入 SSE 响应头并返回写入器。调用方需保证此时尚未写入 body。
func newSSEWriter(w http.ResponseWriter) (*sseWriter, error) {
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

	return &sseWriter{w: w, fl: flusher}, nil
}

// write 写一个事件帧并立即 flush。
func (s *sseWriter) write(event string, data any) error {
	payload, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("序列化 SSE 载荷失败: %w", err)
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, err := fmt.Fprintf(s.w, "event: %s\ndata: %s\n\n", event, payload); err != nil {
		return err
	}
	s.fl.Flush()
	return nil
}

// delta 增量文本。
func (s *sseWriter) delta(text string) error {
	return s.write("delta", map[string]string{"text": text})
}

// reset 要求客户端清空已渲染内容。
func (s *sseWriter) reset() error {
	return s.write("reset", struct{}{})
}

// error 错误提示。
func (s *sseWriter) error(message string) error {
	return s.write("error", map[string]string{"message": message})
}

// done 本轮结束。
func (s *sseWriter) done(messageID uint64, status string) error {
	return s.write("done", map[string]any{
		"message_id": messageID,
		"status":     status,
	})
}

// heartbeat 周期性发心跳，直到 done 关闭。
// 写失败说明连接已断，通过 onBroken 通知调用方取消本轮。
func (s *sseWriter) heartbeat(done <-chan struct{}, interval time.Duration, onBroken func()) {
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
			s.mu.Lock()
			_, err := fmt.Fprint(s.w, ": ping\n\n")
			if err == nil {
				s.fl.Flush()
			}
			s.mu.Unlock()
			if err != nil {
				if onBroken != nil {
					onBroken()
				}
				return
			}
		}
	}
}
