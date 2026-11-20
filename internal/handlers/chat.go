package handlers

import (
	"context"
	"errors"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"mentorly/internal/auth"
	"mentorly/internal/config"
	"mentorly/internal/dto"
	"mentorly/internal/harness"
	"mentorly/internal/services"
	"mentorly/pkg/response"
	"mentorly/pkg/sse"
)

// ChatHandler 对话相关接口。
type ChatHandler struct {
	svc *services.ChatService
	cfg *config.Config
}

// NewChatHandler 构造 handler。
func NewChatHandler(svc *services.ChatService, cfg *config.Config) *ChatHandler {
	return &ChatHandler{svc: svc, cfg: cfg}
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
	resp, err := h.svc.CreateSession(c.Request.Context(), userID, &req)
	if err != nil {
		response.ServerError(c, "创建会话失败")
		return
	}
	response.OK(c, resp)
}

// ListSessions 会话列表
func (h *ChatHandler) ListSessions(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))

	userID := auth.CurrentUserID(c)
	list, err := h.svc.ListSessions(c.Request.Context(), userID, limit)
	if err != nil {
		response.ServerError(c, "查询会话列表失败")
		return
	}
	response.OK(c, list)
}

// RenameSession 重命名会话
func (h *ChatHandler) RenameSession(c *gin.Context) {
	var req dto.RenameSessionReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	userID := auth.CurrentUserID(c)
	if err := h.svc.RenameSession(c.Request.Context(), userID, c.Param("id"), &req); err != nil {
		if errors.Is(err, services.ErrSessionNotFound) {
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
	if err := h.svc.DeleteSession(c.Request.Context(), userID, c.Param("id")); err != nil {
		if errors.Is(err, services.ErrSessionNotFound) {
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
	list, err := h.svc.ListMessages(c.Request.Context(), userID, c.Param("id"), beforeID, limit)
	if err != nil {
		if errors.Is(err, services.ErrSessionNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		response.ServerError(c, "查询消息失败")
		return
	}
	response.OK(c, list)
}

// SendMessage 发送消息，返回 SSE 流。
//
// 时序关键点：PrepareTurn（校验 + 加锁 + 落库 user 消息）必须在写出
// SSE 响应头之前完成——404/403/409/400 需要标准 JSON 状态码。
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

	turn, err := h.svc.PrepareTurn(c.Request.Context(), userID, sessionID, req.Content)
	if err != nil {
		switch {
		case errors.Is(err, services.ErrChatUnavailable):
			response.Unavailable(c, "对话能力未启用（未配置 llm.api_key）")
		case errors.Is(err, services.ErrSessionNotFound):
			response.NotFound(c, "会话不存在")
		case errors.Is(err, harness.ErrSessionBusy):
			response.Fail(c, http.StatusConflict, response.CodeConflict, harness.ErrSessionBusy.Error())
		case errors.Is(err, harness.ErrEmptyQuestion):
			response.BadRequest(c, harness.ErrEmptyQuestion.Error())
		default:
			response.ServerError(c, "发送消息失败")
		}
		return
	}

	// 全局 WriteTimeout=90s 对 SSE 太短：这里取消本请求的写超时。
	// SetWriteDeadline 失败时不影响功能，仅可能被超时切断，故忽略错误。
	rc := http.NewResponseController(c.Writer)
	_ = rc.SetWriteDeadline(time.Time{})

	writer, err := sse.NewWriter(c.Writer)
	if err != nil {
		// 响应头已写出一部分，此时只能中断；确保释放锁。
		turn.Release()
		return
	}

	// 关键：不能只依赖 c.Request.Context()。
	// net/http 在客户端断开时并不保证立刻取消 Request.Context（尤其当
	// 服务端正在写数据、尚未触及读方向时），而我们真正的断连信号是「写失败」。
	// 因此这里派生一个可主动取消的 ctx，写失败时立即取消，
	// 让 Harness 把本轮按 cancelled 收口，而不是继续生成并落库成 completed。
	runCtx, cancelRun := context.WithCancel(c.Request.Context())
	defer cancelRun()

	// 心跳与 delta 共用同一 Writer；心跳写失败同样说明连接已断。
	done := make(chan struct{})
	defer close(done)

	go writer.Heartbeat(done, h.cfg.Chat.Heartbeat, cancelRun)

	h.svc.Harness().RunTurn(runCtx, turn, func(f sse.Frame) {
		if err := writer.Write(f); err != nil {
			// 连接已断：取消本轮，Harness 会用 WithoutCancel 落库 cancelled。
			cancelRun()
		}
	})
}

// GetMemory 查看长期记忆
func (h *ChatHandler) GetMemory(c *gin.Context) {
	userID := auth.CurrentUserID(c)
	mem, err := h.svc.GetMemory(c.Request.Context(), userID)
	if err != nil {
		response.ServerError(c, "读取记忆失败")
		return
	}
	response.OK(c, mem)
}

// UpdateMemory 手动编辑记忆
func (h *ChatHandler) UpdateMemory(c *gin.Context) {
	var req dto.UpdateMemoryReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	userID := auth.CurrentUserID(c)
	if err := h.svc.UpdateMemory(c.Request.Context(), userID, req.Content); err != nil {
		if errors.Is(err, services.ErrMemoryTooLong) {
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
	if err := h.svc.ClearMemory(c.Request.Context(), userID); err != nil {
		response.ServerError(c, "清空记忆失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}
