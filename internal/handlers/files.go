package handlers

import (
	"errors"
	"io"
	"net/url"
	"os"
	"path"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"mentorly/internal/dto"
	"mentorly/internal/handlers/response"
	"mentorly/internal/middleware"
	"mentorly/internal/service"
)

// FilesHandler 统一承载附件上传/下载与会话工作区文件列表/下载。
type FilesHandler struct {
	attachments *service.Attachments
	workspace   *service.Workspace
}

func NewFilesHandler(attachments *service.Attachments, workspace *service.Workspace) *FilesHandler {
	return &FilesHandler{attachments: attachments, workspace: workspace}
}

func (h *FilesHandler) UploadAttachment(c *gin.Context) {
	userID := middleware.MustUser(c).UserID
	conversationID := c.PostForm("conversation_id")

	fh, err := c.FormFile("file")
	if err != nil {
		response.BadRequest(c, "缺少 file 字段或上传格式错误")
		return
	}

	maxBytes := h.attachments.MaxBytes()
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

	a, err := h.attachments.Save(c.Request.Context(), userID, conversationID, fh.Filename, f)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrConversationNotFound):
			response.NotFound(c, "会话不存在")
		case errors.Is(err, service.ErrInvalidUpload):
			response.BadRequest(c, err.Error())
		default:
			zap.L().Error("上传附件失败", zap.Error(err))
			response.ServerError(c, "上传附件失败")
		}
		return
	}

	response.OK(c, dto.AttachmentResp{
		ID: a.ID, Filename: a.Filename, Kind: a.Kind, MIME: a.MIME, Size: a.Size,
		TextLength: len([]rune(a.Text)), ExtractError: a.ExtractError,
		DownloadURL: "/api/v1/attachments/" + a.ID + "/download",
	})
}

func (h *FilesHandler) DownloadAttachment(c *gin.Context) {
	a, err := h.attachments.Get(c.Request.Context(), middleware.MustUser(c).UserID, c.Param("id"))
	if err != nil {
		if errors.Is(err, service.ErrAttachmentNotFound) {
			response.NotFound(c, "附件不存在")
			return
		}
		response.ServerError(c, "查询附件失败")
		return
	}

	f, err := h.attachments.Open(a)
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
		zap.L().Debug("下载附件时连接中断", zap.Error(err))
	}
}

func (h *FilesHandler) ListWorkspace(c *gin.Context) {
	rows, err := h.workspace.List(c.Request.Context(), middleware.MustUser(c).UserID, c.Param("id"))
	if err != nil {
		switch {
		case errors.Is(err, service.ErrConversationNotFound):
			response.NotFound(c, "会话不存在")
		case errors.Is(err, service.ErrUnsafePath):
			response.BadRequest(c, "会话 ID 不合法")
		default:
			zap.L().Error("读取工作区失败", zap.Error(err))
			response.ServerError(c, "读取工作区失败")
		}
		return
	}
	out := make([]dto.FileResp, 0, len(rows))
	convID := c.Param("id")
	for _, f := range rows {
		out = append(out, dto.FileResp{
			Name:        f.Name,
			Path:        "/workspace/" + f.Name,
			Size:        f.Size,
			ModifiedAt:  f.ModifiedAt.Format("2006-01-02T15:04:05Z07:00"),
			DownloadURL: "/api/v1/workspaces/" + convID + "/files/" + url.PathEscape(f.Name),
		})
	}
	response.OK(c, out)
}

func (h *FilesHandler) DownloadWorkspace(c *gin.Context) {
	name := strings.TrimPrefix(c.Param("name"), "/")
	f, info, err := h.workspace.Open(c.Request.Context(), middleware.MustUser(c).UserID, c.Param("id"), name)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrConversationNotFound):
			response.NotFound(c, "会话不存在")
		case errors.Is(err, service.ErrUnsafePath):
			response.BadRequest(c, "文件名不合法")
		case errors.Is(err, os.ErrNotExist):
			response.NotFound(c, "文件不存在")
		default:
			response.NotFound(c, "文件不存在")
		}
		return
	}
	defer f.Close()

	c.Header("Content-Type", mimeOfName(name))
	c.Header("Content-Disposition", contentDisposition(name))
	c.Header("Content-Length", strconv.FormatInt(info.Size(), 10))
	c.Header("X-Content-Type-Options", "nosniff")
	if _, err := io.Copy(c.Writer, f); err != nil {
		zap.L().Debug("下载工作区文件时连接中断", zap.Error(err))
	}
}

func contentDisposition(filename string) string {
	safe := url.PathEscape(filename)
	ascii := "file"
	if ext := path.Ext(filename); ext != "" {
		ascii = "file" + ext
	}
	return `attachment; filename="` + ascii + `"; filename*=UTF-8''` + safe
}

func mimeOfName(name string) string {
	switch strings.ToLower(path.Ext(name)) {
	case ".svg":
		return "image/svg+xml"
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".pptx":
		return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
	case ".docx":
		return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
	case ".pdf":
		return "application/pdf"
	case ".mp4":
		return "video/mp4"
	case ".md":
		return "text/markdown; charset=utf-8"
	case ".json", ".excalidraw":
		return "application/json"
	case ".txt":
		return "text/plain; charset=utf-8"
	default:
		return "application/octet-stream"
	}
}
