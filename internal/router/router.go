package router

import (
	"github.com/gin-gonic/gin"

	"mentorly/internal/handlers"
)

// Register 只连接 HTTP 路径与已装配的 Handler。
func Register(engine *gin.Engine, authMW gin.HandlerFunc, auth *handlers.AuthHandler, chat *handlers.ChatHandler, file *handlers.FileHandler, workspace *handlers.WorkspaceHandler, health *handlers.HealthHandler) {
	engine.GET("/healthz", health.Live)
	engine.GET("/readyz", health.Ready)
	v1 := engine.Group("/api/v1")
	authGroup := v1.Group("/auth")
	authGroup.POST("/register", auth.Register)
	authGroup.POST("/login", auth.Login)
	v1.GET("/profile", authMW, auth.Profile)

	conversations := v1.Group("/conversations", authMW)
	conversations.POST("", chat.CreateConversation)
	conversations.GET("", chat.ListConversations)
	conversations.PATCH("/:id", chat.RenameConversation)
	conversations.DELETE("/:id", chat.DeleteConversation)
	conversations.GET("/:id/messages", chat.ListMessages)
	conversations.POST("/:id/messages", chat.SendMessage)

	files := v1.Group("/attachments", authMW)
	files.POST("", file.Upload)
	files.GET("/:id", file.Get)
	files.GET("/:id/download", file.Download)

	workspaces := v1.Group("/workspaces", authMW)
	workspaces.GET("/:id/files", workspace.List)
	workspaces.GET("/:id/files/*name", workspace.Download)
}
