package handlers

import (
	"errors"

	"github.com/gin-gonic/gin"

	"mentorly/internal/dto"
	"mentorly/internal/handlers/response"
	"mentorly/internal/middleware"
	"mentorly/internal/service/auth"
)

type AuthHandler struct {
	svc *auth.Service
}

func NewAuthHandler(svc *auth.Service) *AuthHandler {
	return &AuthHandler{svc: svc}
}

func (h *AuthHandler) Register(c *gin.Context) {
	var req dto.RegisterReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	cred, err := h.svc.Register(c.Request.Context(), req.Username, req.Email, req.Password)
	if err != nil {
		if errors.Is(err, auth.ErrEmailTaken) {
			response.Conflict(c, auth.ErrEmailTaken.Error())
			return
		}
		response.ServerError(c, "注册失败，请稍后重试")
		return
	}
	response.OK(c, dto.LoginResp{Token: cred.Token, User: toUserResp(cred.User)})
}

func (h *AuthHandler) Login(c *gin.Context) {
	var req dto.LoginReq
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	cred, err := h.svc.Login(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		switch {
		case errors.Is(err, auth.ErrInvalidCredentials):
			response.Unauthorized(c, auth.ErrInvalidCredentials.Error())
		case errors.Is(err, auth.ErrDisabled):
			response.Forbidden(c, auth.ErrDisabled.Error())
		default:
			response.ServerError(c, "登录失败，请稍后重试")
		}
		return
	}
	response.OK(c, dto.LoginResp{Token: cred.Token, User: toUserResp(cred.User)})
}

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

func toUserResp(u *auth.User) dto.UserResp {
	return dto.UserResp{ID: u.ID, Username: u.Username, Email: u.Email}
}
