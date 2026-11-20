// Package router 负责组装 Gin 引擎、依赖与全部路由。
package router

import (
	"github.com/cloudwego/eino/components/model"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"gorm.io/gorm"

	"mentorly/internal/agent"
	"mentorly/internal/auth"
	"mentorly/internal/config"
	"mentorly/internal/dao"
	"mentorly/internal/handlers"
	"mentorly/internal/harness"
	"mentorly/internal/llm"
	"mentorly/internal/memory"
	"mentorly/internal/middleware"
	"mentorly/internal/services"
)

// Deps 是路由层需要的外部依赖集合。
type Deps struct {
	Config *config.Config
	DB     *gorm.DB
	Redis  *redis.Client
	JWT    *auth.Jwt
	LLM    model.ToolCallingChatModel
	Log    *zap.Logger
}

// App 汇总需要随进程生命周期管理的组件。
type App struct {
	Engine *gin.Engine
	// TitleGen 需要在退出时等待在途任务
	TitleGen *harness.TitleGenerator
}

// New 组装中间件、依赖与路由表。
func New(d Deps) *App {
	cfg := d.Config
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}

	if cfg.APP.IsProd() {
		gin.SetMode(gin.ReleaseMode)
	}

	// ---------- 数据访问层 ----------
	chatRepo := dao.NewChatRepo(d.DB)
	memoryRepo := dao.NewMemoryRepo(d.DB)
	lockRepo := dao.NewLockRepo(d.Redis)
	sessionStore := dao.NewSessionStore(chatRepo, memoryRepo)

	// ---------- LLM 适配 ----------
	// Completer 为 nil 表示未配置模型：Harness 不可用，/chat 相关接口返回 503。
	completer := llm.NewCompleter(d.LLM)

	// ---------- Pre-Run 上下文管道 ----------
	var (
		tutorHarness *harness.TutorHarness
		titleGen     *harness.TitleGenerator
	)

	if completer != nil {
		memCfg := memory.Config{
			HistoryMaxMessages:      cfg.Chat.HistoryMaxMessages,
			HistoryBudgetTokens:     cfg.Chat.HistoryBudgetTokens,
			CompressTriggerTokens:   cfg.Chat.CompressTriggerTokens,
			CompressTriggerMessages: cfg.Chat.CompressTriggerMessages,
			CompressSourceMaxChars:  cfg.Chat.CompressSourceMaxChars,
			KeepRecentTurns:         cfg.Chat.KeepRecentTurns,
			MemoryMinTurns:          cfg.Chat.MemoryMinTurns,
			MemoryMinTokens:         cfg.Chat.MemoryMinTokens,
			MemoryMaxChars:          cfg.Chat.MemoryMaxChars,
			WorkspaceRoot:           cfg.Chat.WorkspaceDir,
			LLMTimeout:              cfg.Chat.RunTimeout,
		}

		ctxBuilder := memory.NewBuilder(completer, sessionStore, sessionStore, memCfg, log)

		// remember 工具通过 MemoryAppender 接口拿到 sessionStore，
		// agent 包因此不依赖 dao。
		remember := agent.NewRememberTool(sessionStore)
		agentBuilder := agent.NewBuilder(d.LLM, cfg.Chat.SkillsDir, remember)

		titleGen = harness.NewTitleGenerator(completer, chatRepo, cfg.Chat.TitleWorkers, cfg.Chat.TitleTimeout, log)

		tutorHarness = harness.New(harness.Deps{
			Config:   cfg,
			Chat:     chatRepo,
			Memory:   memoryRepo,
			Lock:     lockRepo,
			Builder:  agentBuilder,
			Context:  ctxBuilder,
			Log:      log,
			TitleGen: titleGen,
		})
	}

	// ---------- 业务层 ----------
	userService := services.NewUserService(dao.NewUserRepo(d.DB), d.JWT)
	chatService := services.NewChatService(chatRepo, memoryRepo, tutorHarness, cfg.Chat.MemoryMaxChars)

	// ---------- HTTP 层 ----------
	userHandler := handlers.NewUserHandler(userService)
	chatHandler := handlers.NewChatHandler(chatService, cfg)
	healthHandler := handlers.NewHealthHandler(d.DB, d.Redis)

	engine := gin.New()
	engine.Use(
		middleware.RequestID(),
		middleware.Logger(),
		middleware.Recovery(),
		middleware.CORS(nil),
	)
	engine.NoRoute(middleware.NoRoute())

	engine.GET("/healthz", healthHandler.Live)
	engine.GET("/readyz", healthHandler.Ready)

	v1 := engine.Group("/api/v1")

	// 公开接口
	authGroup := v1.Group("/auth")
	{
		authGroup.POST("/register", userHandler.Register)
		authGroup.POST("/login", userHandler.Login)
	}

	// 需要登录的接口
	authorized := v1.Group("")
	// 除签名与有效期外，还回查用户是否仍然存在且未被禁用，
	// 使停用/删号能立即失效，而不必等到 token 过期。
	authorized.Use(auth.Middleware(d.JWT, userService))
	{
		authorized.GET("/profile", userHandler.Profile)

		chatGroup := authorized.Group("/chat")
		{
			chatGroup.POST("/sessions", chatHandler.CreateSession)
			chatGroup.GET("/sessions", chatHandler.ListSessions)
			chatGroup.PATCH("/sessions/:id", chatHandler.RenameSession)
			chatGroup.DELETE("/sessions/:id", chatHandler.DeleteSession)
			chatGroup.GET("/sessions/:id/messages", chatHandler.ListMessages)
			chatGroup.POST("/sessions/:id/messages", chatHandler.SendMessage)

			chatGroup.GET("/memory", chatHandler.GetMemory)
			chatGroup.PUT("/memory", chatHandler.UpdateMemory)
			chatGroup.DELETE("/memory", chatHandler.ClearMemory)
		}
	}

	return &App{Engine: engine, TitleGen: titleGen}
}
