// Package handlers 是 HTTP 入口：解析请求、编码 SSE 事件帧、处理文件上传与下载。
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
	lg := d.Log
	if lg == nil {
		lg = zap.NewNop()
	}
	return &ChatHandler{service: d.Service, harness: d.Harness, agent: d.Agent, heartbeat: hb, runTimeout: rt, log: lg}
}

func (h *ChatHandler) CreateConversation(c *gin.Context) {
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

func (h *ChatHandler) ListConversations(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))
	list, err := h.service.ListConversations(c.Request.Context(), middleware.MustUser(c).UserID, limit)
	if err != nil {
		h.log.Error("查询会话列表失败", zap.Error(err))
		response.ServerError(c, "查询会话列表失败")
		return
	}
	out := make([]dto.ConversationResp, 0, len(list))
	for i := range list {
		out = append(out, toConversationResp(&list[i]))
	}
	response.OK(c, out)
}

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

func (h *ChatHandler) DeleteConversation(c *gin.Context) {
	err := h.service.DeleteConversation(c.Request.Context(), c.Param("id"), middleware.MustUser(c).UserID)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrConversationBusy):
			response.Conflict(c, err.Error())
		case errors.Is(err, service.ErrConversationNotFound):
			response.NotFound(c, "会话不存在")
		default:
			h.log.Error("删除会话失败", zap.Error(err))
			response.ServerError(c, "删除会话失败")
		}
		return
	}
	response.OK(c, gin.H{"ok": true})
}

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

// SendMessage 按固定顺序执行：Service.Prepare -> Harness.Prepare -> Service.SaveUser -> Agent.Run -> Service.SaveResult。
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

	runCtxTimeout, cancel := context.WithTimeout(ctx, h.runTimeout)
	defer cancel()

	w := newSSEWriter(c, h.heartbeat, func(err error) {
		logger.Warn("[SSE 心跳失败]", logutil.Content("错误", err.Error()))
		cancel()
	})
	defer w.close()

	sink := func(ev service.Event) error {
		if err := w.writeEvent(ev); err != nil {
			logger.Warn("[SSE 写入失败]", zap.String("事件", ev.Type), logutil.Content("错误", err.Error()))
			cancel()
			return err
		}
		return nil
	}

	res := h.agent.Run(runCtxTimeout, rc, sink)
	h.service.SaveResult(runCtxTimeout, runCtx, res, sink)
}

func toConversationResp(c *service.Conversation) dto.ConversationResp {
	return dto.ConversationResp{ID: c.ID, Title: c.Title, CreatedAt: c.CreatedAt, UpdatedAt: c.UpdatedAt}
}

func toMessageList(rows []service.MessageView) []dto.MessageResp {
	out := make([]dto.MessageResp, 0, len(rows))
	for i := range rows {
		m := &rows[i]
		resp := dto.MessageResp{
			ID: m.ID, Role: m.Role, Content: m.Content, Status: m.Status,
			Tokens: m.Tokens, AttachmentIDs: m.AttachmentIDs, CreatedAt: m.CreatedAt,
		}
		if len(m.Attachments) > 0 {
			resp.Attachments = make([]dto.AttachmentBrief, 0, len(m.Attachments))
			for _, a := range m.Attachments {
				resp.Attachments = append(resp.Attachments, dto.AttachmentBrief{
					ID: a.ID, Filename: a.Filename, Kind: a.Kind, MIME: a.MIME, Size: a.Size,
					DownloadURL: "/api/v1/attachments/" + a.ID + "/download",
				})
			}
		}
		out = append(out, resp)
	}
	return out
}

// ---------- SSE writer ----------

type sseWriter struct {
	gin              *gin.Context
	flusher          http.Flusher
	mu               sync.Mutex
	closed           bool
	stopHB           chan struct{}
	once             sync.Once
	onHeartbeatError func(error)
}

func newSSEWriter(c *gin.Context, heartbeat time.Duration, onHeartbeatError func(error)) *sseWriter {
	c.Header("Content-Type", "text/event-stream; charset=utf-8")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
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

func (w *sseWriter) close() {
	w.once.Do(func() {
		close(w.stopHB)
		w.mu.Lock()
		w.closed = true
		w.mu.Unlock()
	})
}
