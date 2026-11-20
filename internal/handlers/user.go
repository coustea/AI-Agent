// Package handlers 是 HTTP 层，只做参数绑定、调用 service、映射响应。
// 业务规则一律下沉到 services，这里不写 SQL，也不做复杂判断。
package handlers

import (
	"errors"

	"github.com/gin-gonic/gin"

	"mentorly/internal/auth"
	"mentorly/internal/dto"
	"mentorly/internal/services"
	"mentorly/pkg/response"
)

// UserHandler 用户相关接口
type UserHandler struct {
	svc *services.UserService
}

func NewUserHandler(svc *services.UserService) *UserHandler {
	return &UserHandler{svc: svc}
}

// Register 用户注册
func (h *UserHandler) Register(c *gin.Context) {
	var req dto.RegisterReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	resp, err := h.svc.Register(&req)
	if err != nil {
		// 唯一键冲突说明邮箱已被占用，属于客户端可修正的错误，返回 409。
		if errors.Is(err, services.ErrEmailTaken) {
			response.Conflict(c, services.ErrEmailTaken.Error())
			return
		}
		response.ServerError(c, "注册失败，请稍后重试")
		return
	}

	response.OK(c, resp)
}

// Login 用户登录
func (h *UserHandler) Login(c *gin.Context) {
	var req dto.LoginReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	resp, err := h.svc.Login(&req)
	if err != nil {
		if errors.Is(err, services.ErrInvalidCredentials) {
			response.Unauthorized(c, services.ErrInvalidCredentials.Error())
			return
		}
		// 账号被禁用属于「凭证本身有效但无权使用」，用 403 区分于密码错误。
		if errors.Is(err, services.ErrUserDisabled) {
			response.Forbidden(c, services.ErrUserDisabled.Error())
			return
		}
		response.ServerError(c, "登录失败，请稍后重试")
		return
	}

	response.OK(c, resp)
}

// Profile 获取当前登录用户信息
func (h *UserHandler) Profile(c *gin.Context) {
	userID := auth.CurrentUserID(c)
	if userID == "" {
		response.Unauthorized(c, "未登录")
		return
	}

	profile, err := h.svc.GetProfile(userID)
	if err != nil {
		if errors.Is(err, services.ErrUserNotFound) {
			response.NotFound(c, services.ErrUserNotFound.Error())
			return
		}
		response.ServerError(c, "查询用户失败")
		return
	}

	response.OK(c, profile)
}
