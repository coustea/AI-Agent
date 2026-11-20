package auth

import "github.com/gin-gonic/gin"

// RegisterPublic 注册公开端点（注册、登录）。
func RegisterPublic(rg *gin.RouterGroup, h *Handler) {
	g := rg.Group("/auth")
	g.POST("/register", h.Register)
	g.POST("/login", h.Login)
}

// RegisterProtected 注册需要登录的端点。
func RegisterProtected(rg *gin.RouterGroup, authMW gin.HandlerFunc, h *Handler) {
	g := rg.Group("")
	g.Use(authMW)
	g.GET("/profile", h.Profile)
}
