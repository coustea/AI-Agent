// Package middleware 提供 Gin 全局中间件。
package middleware

import (
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"mentorly/internal/response"
)

// 上下文键名
const (
	CtxRequestID = "request_id"
)

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
func Logger() gin.HandlerFunc {
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
		if len(c.Errors) > 0 {
			fields = append(fields, zap.String("errors", c.Errors.String()))
		}

		// 只有真正的服务端故障才记 error 并带堆栈。
		// 5xx 中也有「预期内」的情形（如未配置 AI 能力返回 503），
		// 一律按 error 处理会淹没真正的异常，所以额外用 handler 标记区分。
		expected := c.GetBool(response.CtxExpectedError)
		switch {
		case c.Writer.Status() >= 500 && !expected:
			zap.L().Error("request", fields...)
		case c.Writer.Status() >= 500:
			zap.L().Warn("request", append(fields, zap.Bool("expected", true))...)
		case c.Writer.Status() >= 400:
			zap.L().Warn("request", fields...)
		default:
			zap.L().Info("request", fields...)
		}
	}
}

// Recovery 捕获 panic，返回统一 500 并记录堆栈。
func Recovery() gin.HandlerFunc {
	return gin.CustomRecovery(func(c *gin.Context, err any) {
		zap.L().Error("panic recovered",
			zap.Any("error", err),
			zap.String("path", c.Request.URL.Path),
		)
		response.ServerError(c, "internal server error")
		c.Abort()
	})
}
