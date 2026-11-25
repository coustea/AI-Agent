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

// WorkspaceHandler 只负责工作区文件的 HTTP 表示。
type WorkspaceHandler struct {
	service *service.Workspace
}

func NewWorkspaceHandler(s *service.Workspace) *WorkspaceHandler {
	return &WorkspaceHandler{service: s}
}

func (h *WorkspaceHandler) List(c *gin.Context) {
	rows, err := h.service.List(c.Request.Context(), middleware.MustUser(c).UserID, c.Param("id"))
	if err != nil {
		if errors.Is(err, service.ErrConversationNotFound) {
			response.NotFound(c, "会话不存在")
			return
		}
		if errors.Is(err, service.ErrUnsafePath) {
			response.BadRequest(c, "会话 ID 不合法")
			return
		}
		zap.L().Error("读取工作区失败", zap.Error(err))
		response.ServerError(c, "读取工作区失败")
		return
	}
	out := make([]dto.FileResp, 0, len(rows))
	for _, f := range rows {
		out = append(out, dto.FileResp{Name: f.Name, Path: "/workspace/" + f.Name, Size: f.Size, ModifiedAt: f.ModifiedAt.Format("2006-01-02T15:04:05Z07:00"), DownloadURL: "/api/v1/workspaces/" + c.Param("id") + "/files/" + url.PathEscape(f.Name)})
	}
	response.OK(c, out)
}

func (h *WorkspaceHandler) Download(c *gin.Context) {
	name := strings.TrimPrefix(c.Param("name"), "/")
	f, info, err := h.service.Open(c.Request.Context(), middleware.MustUser(c).UserID, c.Param("id"), name)
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

// mimeOfName 按扩展名推断 MIME。
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
	case ".json":
		return "application/json"
	case ".excalidraw":
		return "application/json"
	case ".txt":
		return "text/plain; charset=utf-8"
	default:
		return "application/octet-stream"
	}
}
