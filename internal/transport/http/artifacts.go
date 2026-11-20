package http

import (
	"errors"
	"io"
	"net/url"
	"strconv"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"mentorly/internal/capabilities/artifacts"
	"mentorly/internal/response"
)

// ArtifactHandler 是产物查询与下载的 HTTP 入口。
type ArtifactHandler struct {
	svc    *artifacts.Service
	userID func(*gin.Context) string
}

// ArtifactDeps 是产物 handler 的装配参数。
type ArtifactDeps struct {
	Service *artifacts.Service
	UserID  func(*gin.Context) string
}

// NewArtifactHandler 构造 handler。
func NewArtifactHandler(d ArtifactDeps) *ArtifactHandler {
	return &ArtifactHandler{svc: d.Service, userID: d.UserID}
}

func (h *ArtifactHandler) currentUserID(c *gin.Context) string {
	if h.userID == nil {
		return ""
	}
	return h.userID(c)
}

// Register 挂载产物路由。
func (h *ArtifactHandler) Register(rg *gin.RouterGroup, authMW gin.HandlerFunc) {
	g := rg.Group("/artifacts", authMW)
	{
		g.GET("", h.List)
		g.GET("/:id", h.Get)
		g.GET("/:id/download", h.Download)
		g.DELETE("/:id", h.Delete)
	}
}

// ArtifactResp 是产物响应结构。
type ArtifactResp struct {
	ID          string         `json:"id"`
	Kind        string         `json:"kind"`
	Title       string         `json:"title"`
	Status      string         `json:"status"`
	Progress    int            `json:"progress"`
	MIME        string         `json:"mime,omitempty"`
	Size        int64          `json:"size,omitempty"`
	Error       string         `json:"error,omitempty"`
	Meta        map[string]any `json:"meta,omitempty"`
	DownloadURL string         `json:"download_url,omitempty"`
	CreatedAt   string         `json:"created_at"`
}

func toArtifactResp(a *artifacts.Artifact) ArtifactResp {
	out := ArtifactResp{
		ID:        a.ID,
		Kind:      a.Kind,
		Title:     a.Title,
		Status:    a.Status,
		Progress:  a.Progress,
		MIME:      a.MIME,
		Size:      a.Size,
		Error:     a.Error,
		Meta:      a.Meta,
		CreatedAt: a.CreatedAt.Format("2006-01-02T15:04:05Z07:00"),
	}
	if a.Done() {
		out.DownloadURL = "/api/v1/artifacts/" + a.ID + "/download"
	}
	return out
}

// List 列出产物。可按 conversation_id 过滤。
func (h *ArtifactHandler) List(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))

	rows, err := h.svc.Store().List(c.Request.Context(), h.currentUserID(c), c.Query("conversation_id"), limit)
	if err != nil {
		zap.L().Error("查询产物列表失败", zap.Error(err))
		response.ServerError(c, "查询产物列表失败")
		return
	}

	out := make([]ArtifactResp, 0, len(rows))
	for i := range rows {
		// 查询时同步任务状态，保证前端看到的是最新真实状态。
		if err := h.svc.SyncStatus(c.Request.Context(), &rows[i]); err != nil {
			zap.L().Warn("同步产物状态失败", zap.Error(err))
		}
		out = append(out, toArtifactResp(&rows[i]))
	}
	response.OK(c, out)
}

// Get 查询单个产物状态。
func (h *ArtifactHandler) Get(c *gin.Context) {
	a, err := h.svc.Store().GetForUser(c.Request.Context(), c.Param("id"), h.currentUserID(c))
	if err != nil {
		if errors.Is(err, artifacts.ErrNotFound) {
			response.NotFound(c, "产物不存在")
			return
		}
		response.ServerError(c, "查询产物失败")
		return
	}

	if err := h.svc.SyncStatus(c.Request.Context(), a); err != nil {
		zap.L().Warn("同步产物状态失败", zap.Error(err))
	}
	response.OK(c, toArtifactResp(a))
}

// Download 下载产物文件。
//
// 只有 completed 状态才能下载：生成中的文件不完整，
// 让前端下载到半成品比直接拒绝更糟。
func (h *ArtifactHandler) Download(c *gin.Context) {
	a, err := h.svc.Store().GetForUser(c.Request.Context(), c.Param("id"), h.currentUserID(c))
	if err != nil {
		if errors.Is(err, artifacts.ErrNotFound) {
			response.NotFound(c, "产物不存在")
			return
		}
		response.ServerError(c, "查询产物失败")
		return
	}

	if !a.Done() {
		response.Conflict(c, "产物尚未生成完成，当前状态: "+a.Status)
		return
	}

	f, err := h.svc.Store().Open(a)
	if err != nil {
		zap.L().Warn("打开产物文件失败", zap.String("artifact_id", a.ID), zap.Error(err))
		response.NotFound(c, "产物文件已丢失")
		return
	}
	defer f.Close()

	c.Header("Content-Type", a.MIME)
	c.Header("Content-Disposition", contentDisposition(a.Title+""+extOf(a)))
	c.Header("Content-Length", strconv.FormatInt(a.Size, 10))
	if _, err := io.Copy(c.Writer, f); err != nil {
		zap.L().Debug("下载产物时连接中断", zap.Error(err))
	}
}

// Delete 删除产物。
func (h *ArtifactHandler) Delete(c *gin.Context) {
	err := h.svc.Store().DeleteForUser(c.Request.Context(), c.Param("id"), h.currentUserID(c))
	if err != nil {
		if errors.Is(err, artifacts.ErrNotFound) {
			response.NotFound(c, "产物不存在")
			return
		}
		response.ServerError(c, "删除产物失败")
		return
	}
	response.OK(c, gin.H{"ok": true})
}

// contentDisposition 构造带 UTF-8 文件名的 Content-Disposition。
//
// 直接用中文文件名会因非 ASCII 被浏览器丢弃或乱码，
// 因此同时给出 ASCII 回退名与 RFC 5987 的 filename*。
func contentDisposition(filename string) string {
	safe := url.PathEscape(filename)
	ascii := "file"
	if ext := extOfName(filename); ext != "" {
		ascii = "file" + ext
	}
	return `attachment; filename="` + ascii + `"; filename*=UTF-8''` + safe
}

func extOf(a *artifacts.Artifact) string {
	return extOfName(a.File)
}

func extOfName(name string) string {
	for i := len(name) - 1; i >= 0; i-- {
		if name[i] == '.' {
			return name[i:]
		}
		if name[i] == '/' {
			break
		}
	}
	return ""
}
