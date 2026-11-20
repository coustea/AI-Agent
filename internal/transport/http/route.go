package http

import "github.com/gin-gonic/gin"

// Register 把对话路由挂到 gin。
//
// 所有端点都要求登录：对话涉及用户数据，不存在公开的对话接口。
func (h *ChatHandler) Register(rg *gin.RouterGroup, authMW gin.HandlerFunc) {
	g := rg.Group("/conversations", authMW)
	{
		g.POST("", h.CreateConversation)
		g.GET("", h.ListConversations)
		g.PATCH("/:id", h.RenameConversation)
		g.DELETE("/:id", h.DeleteConversation)
		g.GET("/:id/messages", h.ListMessages)
		// SSE 端点：不能有任何写响应头之后的错误返回
		g.POST("/:id/messages", h.SendMessage)
	}
}
