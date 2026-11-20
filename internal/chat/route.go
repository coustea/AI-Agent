package chat

import "github.com/gin-gonic/gin"

// Register 把 chat 模块的路由挂到 rg 上。
//
// 路由前缀由调用方（api 层）决定，本函数只管自己的端点。
// authMW 是认证中间件，由 api 层提供，本模块不 import auth 包。
func Register(rg *gin.RouterGroup, authMW gin.HandlerFunc, h *Handler) {
	g := rg.Group("/chat")
	if authMW != nil {
		g.Use(authMW)
	}

	g.POST("/sessions", h.CreateSession)
	g.GET("/sessions", h.ListSessions)
	g.PATCH("/sessions/:id", h.RenameSession)
	g.DELETE("/sessions/:id", h.DeleteSession)
	g.GET("/sessions/:id/messages", h.ListMessages)
	g.POST("/sessions/:id/messages", h.SendMessage)
}
