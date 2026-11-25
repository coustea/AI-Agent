package middleware

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"mentorly/internal/handlers/response"
)

// CtxRequestID 是请求 id 在上下文中的键。
const CtxRequestID = "request_id"

// RequestID 为每个请求注入唯一 ID，便于日志串联。
// 优先复用上游传入的 X-Request-ID，未传则生成 UUID。
func RequestID() gin.HandlerFunc {
	return func(c *gin.Context) {
		id := c.GetHeader("X-Request-ID")
		if id == "" {
			id = uuid.NewString()
		}
		c.Set(CtxRequestID, id)
		c.Header("X-Request-ID", id)
		c.Next()
	}
}

// Logger 用 zap 输出结构化访问日志，并透传 request_id。
func Logger(log *zap.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		c.Next()

		fields := []zap.Field{
			zap.String("method", c.Request.Method),
			zap.String("path", path),
			zap.Int("status", c.Writer.Status()),
			zap.Duration("latency", time.Since(start)),
			zap.String("ip", c.ClientIP()),
		}
		if query != "" {
			fields = append(fields, zap.String("query", query))
		}
		if id, ok := c.Get(CtxRequestID); ok {
			if s, _ := id.(string); s != "" {
				fields = append(fields, zap.String("request_id", s))
			}
		}
		// Logger 在 c.Next() 之后记录，此时 Auth 中间件已写入身份。
		// 未认证的路由（登录、注册）取不到，就不打这个字段。
		if u, ok := CurrentUser(c); ok {
			fields = append(fields, zap.String("user_id", u.UserID))
		}
		if len(c.Errors) > 0 {
			fields = append(fields, zap.String("errors", c.Errors.String()))
		}

		switch {
		case c.Writer.Status() >= 500:
			log.Error("request", fields...)
		case c.Writer.Status() >= 400:
			log.Warn("request", fields...)
		default:
			log.Info("request", fields...)
		}
	}
}

// Recovery 捕获 panic，返回统一 500 并记录堆栈。
func Recovery(log *zap.Logger) gin.HandlerFunc {
	return gin.CustomRecovery(func(c *gin.Context, err any) {
		log.Error("panic recovered",
			zap.Any("error", err),
			zap.String("path", c.Request.URL.Path),
		)
		response.ServerError(c, "internal server error")
		c.Abort()
	})
}

// CORS 跨域配置，供前端本地联调。
// 生产环境应把 allowOrigins 收敛为真实域名白名单。
func CORS(allowOrigins []string) gin.HandlerFunc {
	allowAll := len(allowOrigins) == 0
	allowed := make(map[string]struct{}, len(allowOrigins))
	for _, o := range allowOrigins {
		allowed[o] = struct{}{}
	}

	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		if origin != "" {
			_, ok := allowed[origin]
			if allowAll || ok {
				c.Header("Access-Control-Allow-Origin", origin)
				c.Header("Access-Control-Allow-Credentials", "true")
			}
		}

		c.Header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin,Content-Type,Accept,Authorization,X-Request-ID")
		c.Header("Access-Control-Expose-Headers", "X-Request-ID")
		c.Header("Access-Control-Max-Age", "86400")

		// 预检请求直接结束，不进入业务链路。
		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

// NoRoute 统一处理 404，避免 gin 返回裸文本。
func NoRoute() gin.HandlerFunc {
	return func(c *gin.Context) {
		response.NotFound(c, "接口不存在: "+c.Request.Method+" "+c.Request.URL.Path)
	}
}
