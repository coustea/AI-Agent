package http

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
	"go.uber.org/zap"

	"mentorly/internal/agents/tutor"
	"mentorly/internal/response"
)

// ChatStore 是 chat handler 需要的持久化能力。
type ChatStore interface {
	CreateConversation(ctx context.Context, userID, title string) (*tutor.Conversation, error)
	ListConversations(ctx context.Context, userID string, limit int) ([]tutor.Conversation, error)
	GetConversation(ctx context.Context, id, userID string) (*tutor.Conversation, error)
	RenameConversation(ctx context.Context, id, userID, title string) error
	DeleteConversation(ctx context.Context, id, userID string) error
	ListMessages(ctx context.Context, conversationID string, limit int) ([]tutor.Message, error)
}

// ChatHandler 是对话的 HTTP 入口。
type ChatHandler struct {
	store        ChatStore
	harness      *tutor.Harness
	runtime      *tutor.Runtime
	agentEnabled bool
	titles       TitleEnqueuer
	heartbeat    time.Duration
	runTimeout   time.Duration
	userID       func(*gin.Context) string
	log          *zap.Logger
}

// TitleEnqueuer 提交标题生成任务。
type TitleEnqueuer interface {
	Enqueue(conversationID, question, answer string)
}

// ChatDeps 是 chat handler 的装配参数。
type ChatDeps struct {
	Store        ChatStore
	Harness      *tutor.Harness
	Runtime      *tutor.Runtime
	AgentEnabled bool
	Titles       TitleEnqueuer
	Heartbeat    time.Duration
	RunTimeout   time.Duration
	UserID       func(*gin.Context) string
	Log          *zap.Logger
}

// NewChatHandler 构造 handler。
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

	return &ChatHandler{
		store:        d.Store,
		harness:      d.Harness,
		runtime:      d.Runtime,
		agentEnabled: d.AgentEnabled,
		titles:       d.Titles,
		heartbeat:    hb,
		runTimeout:   rt,
		userID:       d.UserID,
		log:          log,
	}
}

// currentUserID 取当前用户。
func (h *ChatHandler) currentUserID(c *gin.Context) string {
	if h.userID == nil {
		return ""
	}
	return h.userID(c)
}

// ---------- 会话 CRUD ----------

// CreateConversation 创建会话。
func (h *ChatHandler) CreateConversation(c *gin.Context) {
	// 允许空 body：等价于用默认标题创建。
	var req CreateConversationReq
	if c.Request.ContentLength != 0 {
		if err := c.ShouldBindJSON(&req); err != nil {
			response.BadRequest(c, err.Error())
			return
		}
	}

	conv, err := h.store.CreateConversation(c.Request.Context(), h.currentUserID(c), req.Title)
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

	list, err := h.store.ListConversations(c.Request.Context(), h.currentUserID(c), limit)
	if err != nil {
		h.log.Error("查询会话列表失败", zap.Error(err))
		response.ServerError(c, "查询会话列表失败")
		return
	}
	response.OK(c, toConversationList(list))
}

// RenameConversation 重命名会话。
func (h *ChatHandler) RenameConversation(c *gin.Context) {
	var req RenameConversationReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	err := h.store.RenameConversation(c.Request.Context(), c.Param("id"), h.currentUserID(c), req.Title)
	if err != nil {
		if errors.Is(err, tutor.ErrConversationNotFound) {
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
	err := h.store.DeleteConversation(c.Request.Context(), c.Param("id"), h.currentUserID(c))
	if err != nil {
		if errors.Is(err, tutor.ErrConversationNotFound) {
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
	// 归属校验：会话不属于该用户时返回 404，不泄露是否存在。
	if _, err := h.store.GetConversation(c.Request.Context(), c.Param("id"), h.currentUserID(c)); err != nil {
		if errors.Is(err, tutor.ErrConversationNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		response.ServerError(c, "查询会话失败")
		return
	}

	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "0"))
	msgs, err := h.store.ListMessages(c.Request.Context(), c.Param("id"), limit)
	if err != nil {
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
	if !h.agentEnabled {
		response.Unavailable(c, "对话能力未启用")
		return
	}

	var req SendMessageReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	userID := h.currentUserID(c)
	conversationID := c.Param("id")

	// 准备运行上下文：内含会话归属校验、历史加载、用户消息落库。
	// 这一步失败时还没有写出响应头，可以正常返回状态码。
	runCtx, err := h.harness.Prepare(c.Request.Context(), userID, conversationID, req.Content, req.AttachmentIDs)
	if err != nil {
		switch {
		case errors.Is(err, tutor.ErrConversationNotFound):
			response.NotFound(c, "会话不存在")
		case errors.Is(err, tutor.ErrEmptyQuestion):
			response.BadRequest(c, "消息内容不能为空")
		default:
			h.log.Error("准备运行上下文失败", zap.Error(err))
			response.ServerError(c, "准备对话失败")
		}
		return
	}

	// 单轮总超时：超时后取消 Agent，但落库走 WithoutCancel。
	runCtxTimeout, cancel := context.WithTimeout(c.Request.Context(), h.runTimeout)
	defer cancel()

	w := newSSEWriter(c, h.heartbeat)

	// sink 把业务事件编码成 SSE 帧。
	//
	// 写失败通常意味着客户端断开，返回 error 让 Runtime 停止执行，
	// 避免继续消耗模型与渲染算力。
	sink := func(ev tutor.Event) error {
		return w.writeEvent(ev)
	}

	result := h.runtime.Run(runCtxTimeout, runCtx, sink)

	// 首轮成功后异步生成标题（不影响本轮结果）。
	if runCtx.IsFirstTurn && result.Status == tutor.StatusCompleted && h.titles != nil {
		h.titles.Enqueue(conversationID, runCtx.Question, result.Answer)
	}

	w.close()
}

// ---------- SSE writer ----------

// sseWriter 是 SSE 帧编码器。
//
// 帧契约（与前端约定，变更需同步）：
//
//	event: message          data: {"text":"...","reset":false}
//	event: tool_start       data: {"name":"...","call_id":"..."}
//	event: tool_end         data: {"name":"...","result":"...","elapsed_ms":123}
//	event: artifact_created data: {"artifact_id":"...","kind":"...","status":"queued"}
//	event: error            data: {"message":"..."}
//	event: done             data: {"message_id":1,"status":"completed","elapsed_ms":1234}
//	: ping                  心跳注释行
type sseWriter struct {
	gin     *gin.Context
	flusher http.Flusher
	mu      sync.Mutex
	closed  bool
	stopHB  chan struct{}
	once    sync.Once
}

// newSSEWriter 写出响应头并启动心跳。
func newSSEWriter(c *gin.Context, heartbeat time.Duration) *sseWriter {
	c.Header("Content-Type", "text/event-stream; charset=utf-8")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	// 关闭 nginx 等反向代理的缓冲，否则流式会被攒成一整块。
	c.Header("X-Accel-Buffering", "no")
	c.Status(http.StatusOK)

	w := &sseWriter{
		gin:    c,
		stopHB: make(chan struct{}),
	}
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
				fmt.Fprint(w.gin.Writer, ": ping\n\n")
				if w.flusher != nil {
					w.flusher.Flush()
				}
			}
			w.mu.Unlock()
		}
	}
}

// writeEvent 把业务事件编码为 SSE 帧。
func (w *sseWriter) writeEvent(ev tutor.Event) error {
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

// 确保 io 包被使用（错误包装）。
var _ = io.EOF
