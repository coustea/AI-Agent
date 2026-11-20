package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"mentorly/pkg/response"
)

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
