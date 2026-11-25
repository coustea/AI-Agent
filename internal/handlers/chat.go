// Package handlers 是 HTTP 入口：解析请求、把业务事件编码成 SSE、下载文件。
//
// 鉴权由 middleware 完成，这里只通过 middleware.MustUser 读取已认证身份，
// 不自行解析 Token。它也不含业务判断：会话归属校验与对话流程由 service 负责，
// Handler 按顺序调用 Service、Harness 和 Agent，并处理 HTTP/SSE。
package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"mentorly/internal/agent"
	"mentorly/internal/dto"
	"mentorly/internal/handlers/response"
	"mentorly/internal/middleware"
	"mentorly/internal/service"
	logutil "mentorly/internal/utils/log"
)

// ChatHandler 处理 HTTP/SSE，并顺序调用本轮各阶段。
type ChatHandler struct {
	harness    *agent.Harness
	agent      *agent.Agent
	service    *service.Chat
	heartbeat  time.Duration
	runTimeout time.Duration
	log        *zap.Logger
}

type ChatDeps struct {
	Harness    *agent.Harness
	Agent      *agent.Agent
	Service    *service.Chat
	Heartbeat  time.Duration
	RunTimeout time.Duration
	Log        *zap.Logger
}

func NewChatHandler(d ChatDeps) *ChatHandler {
	hb := d.Heartbeat
	if hb <= 0 {
		hb = 15 * time.Second
	}
	rt := d.RunTimeout
	if rt <= 0 {
		rt = 600 * time.Second
	}
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	return &ChatHandler{service: d.Service, harness: d.Harness, agent: d.Agent, heartbeat: hb, runTimeout: rt, log: log}
}

// ---------- 会话 CRUD ----------

// CreateConversation 创建会话。
func (h *ChatHandler) CreateConversation(c *gin.Context) {
	// 允许空 body：等价于用默认标题创建。
	var req dto.CreateConversationReq
	if c.Request.ContentLength != 0 {
		if err := c.ShouldBindJSON(&req); err != nil {
			response.BadRequest(c, err.Error())
			return
		}
	}

	conv, err := h.service.CreateConversation(c.Request.Context(), middleware.MustUser(c).UserID, req.Title)
	if err != nil {
		h.log.Error("创建会话失败", zap.Error(err))
		response.ServerError(c, "创建会话失败")
		return
	}
	response.OK(c, toConversationResp(conv))
}

// ListConversations 会话列表。
func (h *ChatHandler) ListConversations(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))

	list, err := h.service.ListConversations(c.Request.Context(), middleware.MustUser(c).UserID, limit)
	if err != nil {
		h.log.Error("查询会话列表失败", zap.Error(err))
		response.ServerError(c, "查询会话列表失败")
		return
	}
	response.OK(c, toConversationList(list))
}

// RenameConversation 重命名会话。
func (h *ChatHandler) RenameConversation(c *gin.Context) {
	var req dto.RenameConversationReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	err := h.service.RenameConversation(c.Request.Context(), c.Param("id"), middleware.MustUser(c).UserID, req.Title)
	if err != nil {
		if errors.Is(err, service.ErrConversationNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		h.log.Error("重命名会话失败", zap.Error(err))
		response.ServerError(c, "重命名会话失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}

// DeleteConversation 删除会话。
func (h *ChatHandler) DeleteConversation(c *gin.Context) {
	err := h.service.DeleteConversation(c.Request.Context(), c.Param("id"), middleware.MustUser(c).UserID)
	if err != nil {
		if errors.Is(err, service.ErrConversationBusy) {
			response.Conflict(c, err.Error())
			return
		}
		if errors.Is(err, service.ErrConversationNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		h.log.Error("删除会话失败", zap.Error(err))
		response.ServerError(c, "删除会话失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}

// ListMessages 列出会话消息。
func (h *ChatHandler) ListMessages(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "0"))
	msgs, err := h.service.ListMessages(c.Request.Context(), c.Param("id"), middleware.MustUser(c).UserID, limit)
	if err != nil {
		if errors.Is(err, service.ErrConversationNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		h.log.Error("查询消息失败", zap.Error(err))
		response.ServerError(c, "查询消息失败")
		return
	}
	response.OK(c, toMessageList(msgs))
}

// ---------- 发送消息（SSE） ----------

// SendMessage 发送消息并以 SSE 流式返回。
//
// 关键顺序：所有可能失败的检查（会话归属、参数、Agent 可用性）
// 必须在写出 SSE 响应头之前完成。一旦写出 200 与 text/event-stream，
// 就再也无法改成 404 / 409 / 503。
func (h *ChatHandler) SendMessage(c *gin.Context) {
	if h.agent == nil || !h.agent.Enabled() {
		response.Unavailable(c, "对话能力未启用")
		return
	}

	var req dto.SendMessageReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	userID := middleware.MustUser(c).UserID
	conversationID := c.Param("id")
	logger := h.log.With(zap.String("conversation_id", conversationID))
	ctx := logutil.WithContext(c.Request.Context(), logger)
	logger.Info("[用户输入]", logutil.Content("内容", req.Content), zap.Strings("附件", req.AttachmentIDs))
	logger.Info("[校验会话与附件]")

	// 先校验并锁定会话，再由 Harness 独立装配上下文。
	// 这一步失败时还没有写出响应头，可以正常返回状态码。
	runCtx, err := h.service.Prepare(ctx, userID, conversationID, req.Content, req.AttachmentIDs)
	if err != nil {
		logger.Warn("[校验失败]", logutil.Content("错误", err.Error()))
		switch {
		case errors.Is(err, service.ErrConversationNotFound):
			response.NotFound(c, "会话不存在")
		case errors.Is(err, service.ErrEmptyQuestion):
			response.BadRequest(c, "消息内容不能为空")
		case errors.Is(err, service.ErrInvalidUpload):
			response.BadRequest(c, err.Error())
		case errors.Is(err, service.ErrAttachmentNotFound):
			response.BadRequest(c, "附件不存在或不属于当前用户和会话")
		case errors.Is(err, service.ErrConversationBusy):
			response.Conflict(c, err.Error())
		default:
			h.log.Error("准备运行上下文失败", zap.Error(err))
			response.ServerError(c, "准备对话失败")
		}
		return
	}
	defer runCtx.Close()

	logger.Info("[装配上下文]")
	rc, firstTurn, err := h.harness.Prepare(ctx, userID, conversationID, req.Content, runCtx.Attachments)
	if err != nil {
		logger.Error("[装配上下文失败]", logutil.Content("错误", err.Error()))
		response.ServerError(c, "准备对话失败")
		return
	}
	if err := h.service.SaveUser(ctx, runCtx, firstTurn); err != nil {
		logger.Error("[保存用户消息失败]", logutil.Content("错误", err.Error()))
		response.ServerError(c, "保存消息失败")
		return
	}

	// 单轮总超时：超时后取消 Agent，但落库走 WithoutCancel。
	runCtxTimeout, cancel := context.WithTimeout(ctx, h.runTimeout)
	defer cancel()

	w := newSSEWriter(c, h.heartbeat, func(err error) {
		logger.Warn("[SSE 心跳失败]", logutil.Content("错误", err.Error()))
		cancel()
	})
	defer w.close()

	// sink 把业务事件编码成 SSE 帧。
	//
	// 写失败通常意味着客户端断开，返回 error 让 Chat 停止执行，
	// 避免继续消耗模型与渲染算力。
	sink := func(ev service.Event) error {
		err := w.writeEvent(ev)
		if err != nil {
			logger.Warn("[SSE 写入失败]", zap.String("事件", ev.Type), logutil.Content("错误", err.Error()))
			cancel()
		}
		return err
	}

	res := h.agent.Run(runCtxTimeout, rc, sink)
	h.service.SaveResult(runCtxTimeout, runCtx, res, sink)
}

// ---------- SSE writer ----------

// sseWriter 是 SSE 帧编码器。
//
// 帧契约（与前端约定，变更需同步）：
//
//	event: message    data: {"text":"...","reset":false}
//	event: tool_start data: {"name":"...","call_id":"..."}
//	event: tool_end   data: {"name":"...","result":"...","elapsed_ms":123}
//	event: error      data: {"message":"..."}
//	event: done       data: {"message_id":1,"status":"completed","elapsed_ms":1234}
//	: ping            心跳注释行
type sseWriter struct {
	gin              *gin.Context
	flusher          http.Flusher
	mu               sync.Mutex
	closed           bool
	stopHB           chan struct{}
	once             sync.Once
	onHeartbeatError func(error)
}

// newSSEWriter 写出响应头并启动心跳。
func newSSEWriter(c *gin.Context, heartbeat time.Duration, onHeartbeatError func(error)) *sseWriter {
	c.Header("Content-Type", "text/event-stream; charset=utf-8")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	// 关闭 nginx 等反向代理的缓冲，否则流式会被攒成一整块。
	c.Header("X-Accel-Buffering", "no")
	c.Status(http.StatusOK)

	w := &sseWriter{gin: c, stopHB: make(chan struct{}), onHeartbeatError: onHeartbeatError}
	if f, ok := c.Writer.(http.Flusher); ok {
		w.flusher = f
	}
	c.Writer.Flush()

	if heartbeat > 0 {
		go w.heartbeatLoop(heartbeat)
	}
	return w
}

// heartbeatLoop 定期发送注释行，防止中间代理因空闲断开连接。
func (w *sseWriter) heartbeatLoop(interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-w.stopHB:
			return
		case <-ticker.C:
			w.mu.Lock()
			if !w.closed {
				if _, err := fmt.Fprint(w.gin.Writer, ": ping\n\n"); err != nil {
					w.closed = true
					w.mu.Unlock()
					if w.onHeartbeatError != nil {
						w.onHeartbeatError(err)
					}
					return
				}
				if w.flusher != nil {
					w.flusher.Flush()
				}
			}
			w.mu.Unlock()
		}
	}
}

// writeEvent 把业务事件编码为 SSE 帧。
func (w *sseWriter) writeEvent(ev service.Event) error {
	payload, err := json.Marshal(ev.Data)
	if err != nil {
		return fmt.Errorf("编码事件失败: %w", err)
	}

	w.mu.Lock()
	defer w.mu.Unlock()

	if w.closed {
		return fmt.Errorf("SSE 连接已关闭")
	}

	if _, err := fmt.Fprintf(w.gin.Writer, "event: %s\ndata: %s\n\n", ev.Type, payload); err != nil {
		return fmt.Errorf("写入 SSE 帧失败: %w", err)
	}
	if w.flusher != nil {
		w.flusher.Flush()
	}
	return nil
}

// close 停止心跳并标记关闭。
func (w *sseWriter) close() {
	w.once.Do(func() {
		close(w.stopHB)
		w.mu.Lock()
		w.closed = true
		w.mu.Unlock()
	})
}
