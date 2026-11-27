// Package middleware 提供 Gin 横切能力：认证、访问日志、panic 恢复与 CORS。
package middleware

import (
	"context"
	"errors"
	"strings"

	"github.com/gin-gonic/gin"

	"mentorly/internal/handlers/response"
	"mentorly/internal/service/auth"
)

type Identity struct {
	UserID   string
	Username string
}

const ctxIdentity = "auth_identity"

// UserChecker 由业务层实现，校验 JWT 中的 user_id 在数据库中是否仍然有效。
type UserChecker interface {
	VerifyUser(ctx context.Context, userID string) error
}

// Auth 返回校验 Bearer Token 的 Gin 中间件；checker 为 nil 时仅验签名。
func Auth(j *auth.Jwt, checker UserChecker) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			response.Unauthorized(c, "缺少 Authorization 请求头")
			c.Abort()
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			response.Unauthorized(c, "Authorization 格式应为 Bearer <token>")
			c.Abort()
			return
		}

		claims, err := j.ParseToken(strings.TrimSpace(parts[1]))
		if err != nil {
			if errors.Is(err, auth.ErrExpiredToken) {
				response.Unauthorized(c, "登录已过期，请重新登录")
			} else {
				response.Unauthorized(c, "无效的登录凭证")
			}
			c.Abort()
			return
		}

		if checker != nil {
			if err := checker.VerifyUser(c.Request.Context(), claims.UserID); err != nil {
				switch {
				case errors.Is(err, auth.ErrNotFound):
					response.Unauthorized(c, "账号不存在或已被删除，请重新登录")
				case errors.Is(err, auth.ErrDisabled):
					response.Forbidden(c, "账号已被禁用")
				default:
					_ = c.Error(err)
					response.ServerError(c, "认证校验失败，请稍后重试")
				}
				c.Abort()
				return
			}
		}

		c.Set(ctxIdentity, Identity{UserID: claims.UserID, Username: claims.Username})
		c.Next()
	}
}

func CurrentUser(c *gin.Context) (Identity, bool) {
	v, ok := c.Get(ctxIdentity)
	if !ok {
		return Identity{}, false
	}
	id, ok := v.(Identity)
	return id, ok
}

func MustUser(c *gin.Context) Identity {
	id, ok := CurrentUser(c)
	if !ok {
		panic("middleware: 当前路由缺少认证身份，检查是否漏挂 Auth 中间件")
	}
	return id
}
