package httpapi

import (
	"errors"

	"github.com/gin-gonic/gin"

	"mentorly/internal/httpapi/dto"
	"mentorly/internal/identity"
	"mentorly/internal/platform/auth"
	"mentorly/pkg/response"
)

// UserHandler 用户相关接口
type UserHandler struct {
	svc *identity.Service
}

// NewUserHandler 构造 handler。
func NewUserHandler(svc *identity.Service) *UserHandler {
	return &UserHandler{svc: svc}
}

// Register 用户注册
func (h *UserHandler) Register(c *gin.Context) {
	var req dto.RegisterReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	cred, err := h.svc.Register(c.Request.Context(), req.Username, req.Email, req.Password)
	if err != nil {
		// 唯一键冲突说明邮箱已被占用，属于客户端可修正的错误，返回 409。
		if errors.Is(err, identity.ErrEmailTaken) {
			response.Conflict(c, identity.ErrEmailTaken.Error())
			return
		}
		response.ServerError(c, "注册失败，请稍后重试")
		return
	}
	response.OK(c, toCredentialResp(cred))
}

// Login 用户登录
func (h *UserHandler) Login(c *gin.Context) {
	var req dto.LoginReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	cred, err := h.svc.Login(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		if errors.Is(err, identity.ErrInvalidCredentials) {
			response.Unauthorized(c, identity.ErrInvalidCredentials.Error())
			return
		}
		// 账号被禁用属于「凭证本身有效但无权使用」，用 403 区分于密码错误。
		if errors.Is(err, identity.ErrDisabled) {
			response.Forbidden(c, identity.ErrDisabled.Error())
			return
		}
		response.ServerError(c, "登录失败，请稍后重试")
		return
	}
	response.OK(c, toCredentialResp(cred))
}

// Profile 获取当前登录用户信息
func (h *UserHandler) Profile(c *gin.Context) {
	userID := auth.CurrentUserID(c)
	if userID == "" {
		response.Unauthorized(c, "未登录")
		return
	}

	user, err := h.svc.Profile(c.Request.Context(), userID)
	if err != nil {
		if errors.Is(err, identity.ErrNotFound) {
			response.NotFound(c, identity.ErrNotFound.Error())
			return
		}
		response.ServerError(c, "查询用户失败")
		return
	}
	response.OK(c, toUserResp(user))
}
