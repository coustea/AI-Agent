package http

import (
	"errors"
	"io"
	"strconv"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"mentorly/internal/capabilities/attachments"
	"mentorly/internal/response"
)

// AttachmentHandler 是附件上传与下载的 HTTP 入口。
type AttachmentHandler struct {
	store  *attachments.Store
	userID func(*gin.Context) string
}

// AttachmentDeps 是附件 handler 的装配参数。
type AttachmentDeps struct {
	Store  *attachments.Store
	UserID func(*gin.Context) string
}

// NewAttachmentHandler 构造 handler。
func NewAttachmentHandler(d AttachmentDeps) *AttachmentHandler {
	return &AttachmentHandler{store: d.Store, userID: d.UserID}
}

func (h *AttachmentHandler) currentUserID(c *gin.Context) string {
	if h.userID == nil {
		return ""
	}
	return h.userID(c)
}

// Register 挂载附件路由。
func (h *AttachmentHandler) Register(rg *gin.RouterGroup, authMW gin.HandlerFunc) {
	g := rg.Group("/attachments", authMW)
	{
		g.POST("", h.Upload)
		g.GET("/:id", h.Get)
		g.GET("/:id/download", h.Download)
	}
}

// Upload 上传附件。
//
// 使用 multipart/form-data，字段名 file。
// 大小限制在读取时强制（而不是只靠 MaxMultipartMemory），
// 避免超大文件先被写入临时目录再被拒绝。
func (h *AttachmentHandler) Upload(c *gin.Context) {
	userID := h.currentUserID(c)
	conversationID := c.PostForm("conversation_id")

	fh, err := c.FormFile("file")
	if err != nil {
		response.BadRequest(c, "缺少 file 字段或上传格式错误")
		return
	}

	maxBytes := h.store.Config().MaxBytes
	if fh.Size > maxBytes {
		response.BadRequest(c, "附件超过大小上限 "+strconv.FormatInt(maxBytes>>20, 10)+" MB")
		return
	}

	f, err := fh.Open()
	if err != nil {
		response.ServerError(c, "读取上传文件失败")
		return
	}
	defer f.Close()

	a, err := h.store.Save(c.Request.Context(), userID, conversationID, fh.Filename, f)
	if err != nil {
		// 解析类错误（不支持的格式、超限）属于客户端问题
		response.BadRequest(c, err.Error())
		return
	}

	response.OK(c, toAttachmentResp(a))
}

// Get 查询附件元信息。
func (h *AttachmentHandler) Get(c *gin.Context) {
	a, err := h.store.GetForUser(c.Request.Context(), c.Param("id"), h.currentUserID(c))
	if err != nil {
		if errors.Is(err, attachments.ErrNotFound) {
			response.NotFound(c, "附件不存在")
			return
		}
		response.ServerError(c, "查询附件失败")
		return
	}
	response.OK(c, toAttachmentResp(a))
}

// Download 下载附件原始文件。
func (h *AttachmentHandler) Download(c *gin.Context) {
	a, err := h.store.GetForUser(c.Request.Context(), c.Param("id"), h.currentUserID(c))
	if err != nil {
		if errors.Is(err, attachments.ErrNotFound) {
			response.NotFound(c, "附件不存在")
			return
		}
		response.ServerError(c, "查询附件失败")
		return
	}

	f, err := h.store.Open(a)
	if err != nil {
		zap.L().Warn("打开附件文件失败", zap.String("attachment_id", a.ID), zap.Error(err))
		response.NotFound(c, "附件文件已丢失")
		return
	}
	defer f.Close()

	c.Header("Content-Type", a.MIME)
	c.Header("Content-Disposition", contentDisposition(a.Filename))
	c.Header("Content-Length", strconv.FormatInt(a.Size, 10))
	if _, err := io.Copy(c.Writer, f); err != nil {
		// 响应头已写出，无法再改状态码，只记录。
		zap.L().Debug("下载附件时连接中断", zap.Error(err))
	}
}

// AttachmentResp 是附件响应结构。
type AttachmentResp struct {
	ID           string `json:"id"`
	Filename     string `json:"filename"`
	Kind         string `json:"kind"`
	MIME         string `json:"mime"`
	Size         int64  `json:"size"`
	TextLength   int    `json:"text_length,omitempty"`
	Truncated    bool   `json:"truncated,omitempty"`
	ExtractError string `json:"extract_error,omitempty"`
	DownloadURL  string `json:"download_url"`
}

func toAttachmentResp(a *attachments.Attachment) AttachmentResp {
	return AttachmentResp{
		ID:           a.ID,
		Filename:     a.Filename,
		Kind:         a.Kind,
		MIME:         a.MIME,
		Size:         a.Size,
		TextLength:   len([]rune(a.Text)),
		Truncated:    a.Truncated,
		ExtractError: a.ExtractError,
		DownloadURL:  "/api/v1/attachments/" + a.ID + "/download",
	}
}
