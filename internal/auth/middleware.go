package auth

import (
	"context"
	"errors"
	"strings"

	"github.com/gin-gonic/gin"

	"mentorly/pkg/response"
)

// 上下文键名，handler 通过它们取当前登录用户。
const (
	CtxUserID   = "auth_user_id"
	CtxUsername = "auth_username"
)

// UserStatus 描述 token 中的用户在数据库里的实际状态。
//
// 只验签名并不足以确认身份：签名只证明 token 由本服务签发，
// 不能证明账号此刻仍然存在且可用。用户被删除或禁用后，
// 旧 token 在过期前依然能通过签名校验，因此必须回查状态。
type UserStatus int

const (
	// UserStatusUnknown 无法判定（如查询出错），按服务端故障处理，绝不放行
	UserStatusUnknown UserStatus = iota
	// UserStatusActive 用户存在且可正常使用
	UserStatusActive
	// UserStatusMissing 用户已被删除
	UserStatusMissing
	// UserStatusDisabled 用户已被禁用
	UserStatusDisabled
)

// UserChecker 由业务层实现，把 JWT 中的 user_id 映射为真实用户状态。
// 接口定义在 auth 包内，使 auth 不依赖 dao 或 model。
type UserChecker interface {
	CheckUserStatus(ctx context.Context, userID string) (UserStatus, error)
}

// Middleware 返回校验 Bearer Token 的 Gin 中间件。
// checker 为 nil 时只验签名（跳过用户状态回查），便于测试或无状态场景。
func Middleware(j *Jwt, checker UserChecker) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			response.Unauthorized(c, "缺少 Authorization 请求头")
			c.Abort()
			return
		}

		// 期望格式：Bearer <token>
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			response.Unauthorized(c, "Authorization 格式应为 Bearer <token>")
			c.Abort()
			return
		}

		claims, err := j.ParseToken(strings.TrimSpace(parts[1]))
		if err != nil {
			if errors.Is(err, ErrExpiredToken) {
				response.Unauthorized(c, "登录已过期，请重新登录")
			} else {
				response.Unauthorized(c, "无效的登录凭证")
			}
			c.Abort()
			return
		}

		// 签名与有效期通过后，再核对用户当前是否仍然可用。
		if checker != nil {
			switch status, err := checker.CheckUserStatus(c.Request.Context(), claims.UserID); {
			case err != nil:
				// 查询失败不能放行：否则数据库故障就等于认证失效。
				// 记到 c.Errors，让访问日志带上具体原因。
				_ = c.Error(err)
				response.ServerError(c, "认证校验失败，请稍后重试")
				c.Abort()
				return
			case status == UserStatusMissing:
				response.Unauthorized(c, "账号不存在或已被删除，请重新登录")
				c.Abort()
				return
			case status == UserStatusDisabled:
				response.Forbidden(c, "账号已被禁用")
				c.Abort()
				return
			case status != UserStatusActive:
				_ = c.Error(errors.New("auth: 无法判定用户状态"))
				response.ServerError(c, "认证校验失败，请稍后重试")
				c.Abort()
				return
			}
		}

		c.Set(CtxUserID, claims.UserID)
		c.Set(CtxUsername, claims.Username)
		c.Next()
	}
}

// CurrentUserID 从上下文取当前用户 ID。
func CurrentUserID(c *gin.Context) string {
	v, ok := c.Get(CtxUserID)
	if !ok {
		return ""
	}
	s, _ := v.(string)
	return s
}

// CurrentUsername 从上下文取当前用户名。
// 用户名来自 token 载荷，供日志、展示等场景使用；
// 需要权威信息时仍应以 CurrentUserID 回查数据库。
func CurrentUsername(c *gin.Context) string {
	v, ok := c.Get(CtxUsername)
	if !ok {
		return ""
	}
	s, _ := v.(string)
	return s
}
