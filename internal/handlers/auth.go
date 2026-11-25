package handlers

import (
	"errors"

	"github.com/gin-gonic/gin"

	"mentorly/internal/dto"
	"mentorly/internal/handlers/response"
	"mentorly/internal/middleware"
	"mentorly/internal/service/auth"
)

// Handler 是认证模块的 HTTP 入口。
type AuthHandler struct {
	svc *auth.Service
}

// NewHandler 构造 handler。
func NewAuthHandler(svc *auth.Service) *AuthHandler {
	return &AuthHandler{svc: svc}
}

// Register 用户注册
func (h *AuthHandler) Register(c *gin.Context) {
	var req dto.RegisterReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	cred, err := h.svc.Register(c.Request.Context(), req.Username, req.Email, req.Password)
	if err != nil {
		// 唯一键冲突说明邮箱已被占用，属于客户端可修正的错误，返回 409。
		if errors.Is(err, auth.ErrEmailTaken) {
			response.Conflict(c, auth.ErrEmailTaken.Error())
			return
		}
		response.ServerError(c, "注册失败，请稍后重试")
		return
	}
	response.OK(c, toCredentialResp(cred))
}

// Login 用户登录
func (h *AuthHandler) Login(c *gin.Context) {
	var req dto.LoginReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	cred, err := h.svc.Login(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		if errors.Is(err, auth.ErrInvalidCredentials) {
			response.Unauthorized(c, auth.ErrInvalidCredentials.Error())
			return
		}
		// 账号被禁用属于「凭证本身有效但无权使用」，用 403 区分于密码错误。
		if errors.Is(err, auth.ErrDisabled) {
			response.Forbidden(c, auth.ErrDisabled.Error())
			return
		}
		response.ServerError(c, "登录失败，请稍后重试")
		return
	}
	response.OK(c, toCredentialResp(cred))
}

// Profile 获取当前登录用户信息。
//
// token 里的 username 只用于展示，改名后会过期，
// 因此这里用 UserID 回查数据库拿权威资料。
func (h *AuthHandler) Profile(c *gin.Context) {
	user, err := h.svc.Profile(c.Request.Context(), middleware.MustUser(c).UserID)
	if err != nil {
		if errors.Is(err, auth.ErrNotFound) {
			response.NotFound(c, auth.ErrNotFound.Error())
			return
		}
		response.ServerError(c, "查询用户失败")
		return
	}
	response.OK(c, toUserResp(user))
}
