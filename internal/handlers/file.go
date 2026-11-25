package handlers

import (
	"errors"
	"io"
	"net/url"
	"path"
	"strconv"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"mentorly/internal/handlers/response"
	"mentorly/internal/middleware"
	"mentorly/internal/service"
)

// FileHandler 是附件上传与下载的 HTTP 入口。
//
// 文件名、存储路径、权限由 service 与 repository 处理：
// 这里只做 multipart 解析与响应编码。
type FileHandler struct {
	service *service.Attachments
}

func NewFileHandler(s *service.Attachments) *FileHandler {
	return &FileHandler{service: s}
}

func (h *FileHandler) Upload(c *gin.Context) {
	userID := middleware.MustUser(c).UserID
	conversationID := c.PostForm("conversation_id")

	fh, err := c.FormFile("file")
	if err != nil {
		response.BadRequest(c, "缺少 file 字段或上传格式错误")
		return
	}

	maxBytes := h.service.MaxBytes()
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

	a, err := h.service.Save(c.Request.Context(), userID, conversationID, fh.Filename, f)
	if err != nil {
		if errors.Is(err, service.ErrConversationNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		if errors.Is(err, service.ErrInvalidUpload) {
			response.BadRequest(c, err.Error())
			return
		}
		zap.L().Error("上传附件失败", zap.Error(err))
		response.ServerError(c, "上传附件失败")
		return
	}

	response.OK(c, toAttachmentResp(a))
}

// Get 查询附件元信息。
func (h *FileHandler) Get(c *gin.Context) {
	a, err := h.service.Get(c.Request.Context(), middleware.MustUser(c).UserID, c.Param("id"))
	if err != nil {
		if errors.Is(err, service.ErrAttachmentNotFound) {
			response.NotFound(c, "附件不存在")
			return
		}
		response.ServerError(c, "查询附件失败")
		return
	}
	response.OK(c, toAttachmentResp(a))
}

// Download 下载附件原始文件。
func (h *FileHandler) Download(c *gin.Context) {
	a, err := h.service.Get(c.Request.Context(), middleware.MustUser(c).UserID, c.Param("id"))
	if err != nil {
		if errors.Is(err, service.ErrAttachmentNotFound) {
			response.NotFound(c, "附件不存在")
			return
		}
		response.ServerError(c, "查询附件失败")
		return
	}

	f, err := h.service.Open(a)
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

// contentDisposition 构造带 UTF-8 文件名的 Content-Disposition。
//
// 直接用中文文件名会因非 ASCII 被浏览器丢弃或乱码，
// 因此同时给出 ASCII 回退名与 RFC 5987 的 filename*。
func contentDisposition(filename string) string {
	safe := url.PathEscape(filename)
	ascii := "file"
	if ext := path.Ext(filename); ext != "" {
		ascii = "file" + ext
	}
	return `attachment; filename="` + ascii + `"; filename*=UTF-8''` + safe
}
