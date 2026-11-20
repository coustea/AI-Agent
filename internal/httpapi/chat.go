package httpapi

import (
	"context"
	"errors"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"mentorly/internal/chat"
	"mentorly/internal/httpapi/dto"
	"mentorly/internal/memory"
	"mentorly/internal/platform/auth"
	"mentorly/internal/turn"
	"mentorly/pkg/response"
	"mentorly/pkg/sse"
)

// ChatHandler 对话与会话接口。
type ChatHandler struct {
	sessions *chat.Service
	memory   *memory.Service
	turns    *turn.Orchestrator
	cfg      HandlerConfig
}

// HandlerConfig 是 HTTP 层需要的少量配置。
type HandlerConfig struct {
	// Heartbeat SSE 心跳间隔
	Heartbeat time.Duration
}

// NewChatHandler 构造 handler。
func NewChatHandler(sessions *chat.Service, mem *memory.Service, turns *turn.Orchestrator, cfg HandlerConfig) *ChatHandler {
	if cfg.Heartbeat <= 0 {
		cfg.Heartbeat = 15 * time.Second
	}
	return &ChatHandler{sessions: sessions, memory: mem, turns: turns, cfg: cfg}
}

// CreateSession 创建会话
func (h *ChatHandler) CreateSession(c *gin.Context) {
	// 允许空 body：等价于用默认标题创建会话。
	// 只有在确实带了 body 且解析失败时才报 400。
	var req dto.CreateSessionReq
	if c.Request.ContentLength != 0 {
		if err := c.ShouldBindJSON(&req); err != nil {
			response.BadRequest(c, err.Error())
			return
		}
	}

	userID := auth.CurrentUserID(c)
	sess, err := h.sessions.Create(c.Request.Context(), userID, req.Title)
	if err != nil {
		response.ServerError(c, "创建会话失败")
		return
	}
	response.OK(c, toSessionResp(sess))
}

// ListSessions 会话列表
func (h *ChatHandler) ListSessions(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))

	userID := auth.CurrentUserID(c)
	list, err := h.sessions.List(c.Request.Context(), userID, limit)
	if err != nil {
		response.ServerError(c, "查询会话列表失败")
		return
	}
	response.OK(c, toSessionList(list))
}

// RenameSession 重命名会话
func (h *ChatHandler) RenameSession(c *gin.Context) {
	var req dto.RenameSessionReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	userID := auth.CurrentUserID(c)
	if err := h.sessions.Rename(c.Request.Context(), userID, c.Param("id"), req.Title); err != nil {
		if errors.Is(err, chat.ErrSessionNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		response.ServerError(c, "重命名会话失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}

// DeleteSession 软删除会话
func (h *ChatHandler) DeleteSession(c *gin.Context) {
	userID := auth.CurrentUserID(c)
	if err := h.sessions.Delete(c.Request.Context(), userID, c.Param("id")); err != nil {
		if errors.Is(err, chat.ErrSessionNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		response.ServerError(c, "删除会话失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}

// ListMessages 游标分页查询历史
func (h *ChatHandler) ListMessages(c *gin.Context) {
	beforeID, _ := strconv.ParseUint(c.DefaultQuery("before_id", "0"), 10, 64)
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))

	userID := auth.CurrentUserID(c)
	views, err := h.sessions.Messages(c.Request.Context(), userID, c.Param("id"), beforeID, limit)
	if err != nil {
		if errors.Is(err, chat.ErrSessionNotFound) {
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
// 时序关键点：Prepare（校验 + 加锁 + 落库 user 消息）必须在写出
// SSE 响应头之前完成——404/409/400 需要标准 JSON 状态码。
// 一旦校验通过，立即切换 event-stream 并启动心跳，
// 随后的记忆提取与压缩（可能耗时数秒）由心跳帧保住连接。
func (h *ChatHandler) SendMessage(c *gin.Context) {
	var req dto.SendMessageReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	userID := auth.CurrentUserID(c)
	sessionID := c.Param("id")

	prepared, err := h.turns.Prepare(c.Request.Context(), userID, sessionID, req.Content)
	if err != nil {
		switch {
		case errors.Is(err, turn.ErrUnavailable):
			response.Unavailable(c, "对话能力未启用（未配置 llm.api_key）")
		case errors.Is(err, turn.ErrSessionNotFound):
			response.NotFound(c, "会话不存在")
		case errors.Is(err, turn.ErrBusy):
			response.Fail(c, http.StatusConflict, response.CodeConflict, turn.ErrBusy.Error())
		case errors.Is(err, turn.ErrEmptyQuestion):
			response.BadRequest(c, turn.ErrEmptyQuestion.Error())
		default:
			response.ServerError(c, "发送消息失败")
		}
		return
	}

	// 全局 WriteTimeout 对 SSE 太短：取消本请求的写超时。
	rc := http.NewResponseController(c.Writer)
	_ = rc.SetWriteDeadline(time.Time{})

	writer, err := sse.NewWriter(c.Writer)
	if err != nil {
		// 响应头已写出一部分，此时只能中断；确保释放锁。
		prepared.Release()
		return
	}

	// 关键：不能只依赖 c.Request.Context()。
	// net/http 在客户端断开时并不保证立刻取消 Request.Context（尤其当
	// 服务端正在写数据、尚未触及读方向时），而我们真正的断连信号是「写失败」。
	// 因此派生一个可主动取消的 ctx，写失败时立即取消，
	// 让编排层把本轮按 cancelled 收口，而不是继续生成并落库成 completed。
	runCtx, cancelRun := context.WithCancel(c.Request.Context())
	defer cancelRun()

	// 心跳与 delta 共用同一 Writer；心跳写失败同样说明连接已断。
	done := make(chan struct{})
	defer close(done)

	go writer.Heartbeat(done, h.cfg.Heartbeat, cancelRun)

	// 唯一的编码点：把领域事件翻译成 SSE 帧。
	// 编排核心完全不知道 SSE 的存在。
	h.turns.Run(runCtx, prepared, func(e turn.Event) {
		if err := writer.Write(toFrame(e)); err != nil {
			// 连接已断：取消本轮，编排层会用 WithoutCancel 落库 cancelled。
			cancelRun()
		}
	})
}

// toFrame 把领域事件编码成 SSE 帧。
func toFrame(e turn.Event) sse.Frame {
	switch e.Kind {
	case turn.EventDelta:
		return sse.Delta(e.Text)
	case turn.EventReset:
		return sse.Reset()
	case turn.EventError:
		return sse.Error(e.Text)
	case turn.EventDone:
		return sse.Done(e.MessageID, e.Status)
	default:
		return sse.Ping()
	}
}

// GetMemory 查看长期记忆
func (h *ChatHandler) GetMemory(c *gin.Context) {
	userID := auth.CurrentUserID(c)
	doc, err := h.memory.Get(c.Request.Context(), userID)
	if err != nil {
		response.ServerError(c, "读取记忆失败")
		return
	}
	response.OK(c, toMemoryResp(doc, time.Now()))
}

// UpdateMemory 手动编辑记忆
func (h *ChatHandler) UpdateMemory(c *gin.Context) {
	var req dto.UpdateMemoryReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	userID := auth.CurrentUserID(c)
	if err := h.memory.Update(c.Request.Context(), userID, req.Content); err != nil {
		if errors.Is(err, memory.ErrTooLong) {
			response.BadRequest(c, err.Error())
			return
		}
		response.ServerError(c, "保存记忆失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}

// ClearMemory 清空记忆
func (h *ChatHandler) ClearMemory(c *gin.Context) {
	userID := auth.CurrentUserID(c)
	if err := h.memory.Clear(c.Request.Context(), userID); err != nil {
		response.ServerError(c, "清空记忆失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}
