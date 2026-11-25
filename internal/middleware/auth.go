// Package middleware 提供 Gin 横切能力：认证、访问日志、panic 恢复与 CORS。
//
// 认证只做两件事：校验 Bearer Token，并把身份写入 gin.Context 供 handler 读取。
// 账号状态的判定规则属于业务，通过 UserChecker 接口注入，本包不依赖仓储。
package middleware

import (
	"context"
	"errors"
	"strings"

	"github.com/gin-gonic/gin"

	"mentorly/internal/handlers/response"
	"mentorly/internal/service/auth"
)

// Identity 是认证通过后写入上下文的当前用户身份。
//
// 字段与 JWT 载荷一一对应，不额外回查数据库：username 可能因用户改名
// 而落后于 users 表，需要权威资料时用 UserID 查库（见 /api/v1/profile）。
type Identity struct {
	UserID   string
	Username string
}

// ctxIdentity 是 Identity 在 gin.Context 中的键。
// 用私有常量而非字符串字面量，避免业务代码拼错键名后静默取到零值。
const ctxIdentity = "auth_identity"

// UserChecker 由业务层实现，把 JWT 中的 user_id 映射为真实用户状态。
// 接口定义在 auth 包内，使 auth 不依赖 dao 或 model。
type UserChecker interface {
	CheckUserStatus(ctx context.Context, userID string) (auth.UserStatus, error)
}

// Auth 返回校验 Bearer Token 的 Gin 中间件。
// checker 为 nil 时只验签名（跳过用户状态回查），便于测试或无状态场景。
func Auth(j *auth.Jwt, checker UserChecker) gin.HandlerFunc {
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
			if errors.Is(err, auth.ErrExpiredToken) {
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
			case status == auth.UserStatusMissing:
				response.Unauthorized(c, "账号不存在或已被删除，请重新登录")
				c.Abort()
				return
			case status == auth.UserStatusDisabled:
				response.Forbidden(c, "账号已被禁用")
				c.Abort()
				return
			case status != auth.UserStatusActive:
				_ = c.Error(errors.New("auth: 无法判定用户状态"))
				response.ServerError(c, "认证校验失败，请稍后重试")
				c.Abort()
				return
			}
		}

		// 一次性写入完整身份：handler 只需取一次就拿到 user_id 与 username。
		c.Set(ctxIdentity, Identity{UserID: claims.UserID, Username: claims.Username})
		c.Next()
	}
}

// CurrentUser 取出当前登录用户身份。
// ok 为 false 表示该路由没有经过 Auth 中间件。
func CurrentUser(c *gin.Context) (Identity, bool) {
	v, ok := c.Get(ctxIdentity)
	if !ok {
		return Identity{}, false
	}
	id, ok := v.(Identity)
	if !ok {
		return Identity{}, false
	}
	return id, true
}

// MustUser 取出当前登录用户身份，缺失时 panic。
//
// 只应在挂了 Auth 中间件的路由里调用。缺身份属于装配错误（路由漏挂中间件），
// 让它 panic 由 Recovery 兜成 500，比静默返回空 UserID 更安全：
// 后者会让业务代码以 user_id="" 继续写库。
func MustUser(c *gin.Context) Identity {
	id, ok := CurrentUser(c)
	if !ok {
		panic("middleware: 当前路由缺少认证身份，检查是否漏挂 Auth 中间件")
	}
	return id
}
