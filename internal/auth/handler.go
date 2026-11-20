package auth

import (
	"errors"

	"github.com/gin-gonic/gin"

	"mentorly/internal/response"
)

// Handler 是认证模块的 HTTP 入口。
type Handler struct {
	svc *Service
}

// NewHandler 构造 handler。
func NewHandler(svc *Service) *Handler {
	return &Handler{svc: svc}
}

// Register 用户注册
func (h *Handler) Register(c *gin.Context) {
	var req RegisterReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	cred, err := h.svc.Register(c.Request.Context(), req.Username, req.Email, req.Password)
	if err != nil {
		// 唯一键冲突说明邮箱已被占用，属于客户端可修正的错误，返回 409。
		if errors.Is(err, ErrEmailTaken) {
			response.Conflict(c, ErrEmailTaken.Error())
			return
		}
		response.ServerError(c, "注册失败，请稍后重试")
		return
	}
	response.OK(c, toCredentialResp(cred))
}

// Login 用户登录
func (h *Handler) Login(c *gin.Context) {
	var req LoginReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	cred, err := h.svc.Login(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		if errors.Is(err, ErrInvalidCredentials) {
			response.Unauthorized(c, ErrInvalidCredentials.Error())
			return
		}
		// 账号被禁用属于「凭证本身有效但无权使用」，用 403 区分于密码错误。
		if errors.Is(err, ErrDisabled) {
			response.Forbidden(c, ErrDisabled.Error())
			return
		}
		response.ServerError(c, "登录失败，请稍后重试")
		return
	}
	response.OK(c, toCredentialResp(cred))
}

// Profile 获取当前登录用户信息
func (h *Handler) Profile(c *gin.Context) {
	userID := CurrentUserID(c)
	if userID == "" {
		response.Unauthorized(c, "未登录")
		return
	}

	user, err := h.svc.Profile(c.Request.Context(), userID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			response.NotFound(c, ErrNotFound.Error())
			return
		}
		response.ServerError(c, "查询用户失败")
		return
	}
	response.OK(c, toUserResp(user))
}
