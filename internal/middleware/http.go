package middleware

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"mentorly/internal/handlers/response"
)

const CtxRequestID = "request_id"

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

func CORS() gin.HandlerFunc {
	return func(c *gin.Context) {
		if origin := c.GetHeader("Origin"); origin != "" {
			c.Header("Access-Control-Allow-Origin", origin)
			c.Header("Access-Control-Allow-Credentials", "true")
		}
		c.Header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin,Content-Type,Accept,Authorization,X-Request-ID")
		c.Header("Access-Control-Expose-Headers", "X-Request-ID")
		c.Header("Access-Control-Max-Age", "86400")

		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	}
}

func NoRoute() gin.HandlerFunc {
	return func(c *gin.Context) {
		response.NotFound(c, "接口不存在: "+c.Request.Method+" "+c.Request.URL.Path)
	}
}
