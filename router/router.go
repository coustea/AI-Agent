// Package router 负责组装依赖与路由表。
//
// 这是唯一知道「所有组件如何拼在一起」的地方：
// 每个包只声明自己需要什么，由这里提供实现。
package router

import (
	"github.com/cloudwego/eino/components/model"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"gorm.io/gorm"

	"mentorly/internal/agent"
	"mentorly/internal/auth"
	"mentorly/internal/capability"
	"mentorly/internal/chat"
	"mentorly/internal/config"
	"mentorly/internal/httpapi"
	"mentorly/internal/identity"
	"mentorly/internal/infra"
	"mentorly/internal/memory"
	"mentorly/internal/middleware"
	"mentorly/internal/turn"
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
	TitleGen *memory.TitleGenerator
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

	// ---------- 存储层 ----------
	chatRepo := chat.NewRepo(d.DB)
	memoryRepo := memory.NewRepo(d.DB)
	lock := infra.NewLock(d.Redis)
	userRepo := identity.NewRepo(d.DB)

	// ---------- 域内适配 ----------
	// memory 定义自己需要什么（Transcript / Store），由 Adapters 提供。
	adapters := memory.NewAdapters(chatRepo, memoryRepo)

	// ---------- 编排层 ----------
	// 未配置模型时 completer 为 nil：对话接口返回 503，其余接口照常可用。
	var (
		orchestrator *turn.Orchestrator
		titleGen     *memory.TitleGenerator
	)

	completer := infra.NewCompleter(d.LLM)
	if completer != nil {
		digest := memory.NewDigest(completer, adapters, memory.DigestConfig{
			TriggerTokens:   cfg.Chat.CompressTriggerTokens,
			TriggerMessages: cfg.Chat.CompressTriggerMessages,
			SourceMaxChars:  cfg.Chat.CompressSourceMaxChars,
			KeepRecentTurns: cfg.Chat.KeepRecentTurns,
		}, log)

		consolidator := memory.NewConsolidator(completer, adapters, adapters, memory.Config{
			MinTurns:  cfg.Chat.MemoryMinTurns,
			MinTokens: cfg.Chat.MemoryMinTokens,
			MaxChars:  cfg.Chat.MemoryMaxChars,
			Timeout:   cfg.Chat.RunTimeout,
		}, log)

		// 能力注册表：新增工具只需在此声明一行。
		caps := capability.NewRegistry(
			capability.Memory(adapters),
		)

		agentBuilder := agent.NewBuilder(d.LLM, cfg.Chat.SkillsDir, caps.Tools())

		titleGen = memory.NewTitleGenerator(
			completer, chatRepo, cfg.Chat.TitleWorkers, cfg.Chat.TitleTimeout, log,
		)

		orchestrator = turn.New(turn.Deps{
			Config: turn.Config{
				RunTimeout:          cfg.Chat.RunTimeout,
				MaxSteps:            cfg.Chat.MaxSteps,
				HistoryMaxMessages:  cfg.Chat.HistoryMaxMessages,
				HistoryBudgetTokens: cfg.Chat.HistoryBudgetTokens,
				WorkspaceDir:        cfg.Chat.WorkspaceDir,
				OffloadDir:          cfg.Chat.OffloadRoot,
				SkillsDir:           cfg.Chat.SkillsDir,
				MemoryMaxChars:      cfg.Chat.MemoryMaxChars,
			},
			Sessions: chatRepo,
			Digest:   digest,
			Memory:   consolidator,
			Docs:     adapters,
			Lock:     turn.NewRedisLock(lock),
			Builder:  agentBuilder,
			Title:    titleGen,
			Log:      log,
		})

		log.Info("对话能力已启用", zap.Strings("capabilities", caps.Names()))
	}

	// ---------- 业务服务 ----------
	identityService := identity.NewService(userRepo, d.JWT)
	sessionService := chat.NewService(chatRepo)
	memoryService := memory.NewService(memoryRepo, cfg.Chat.MemoryMaxChars)

	// ---------- HTTP 层 ----------
	userHandler := httpapi.NewUserHandler(identityService)
	chatHandler := httpapi.NewChatHandler(sessionService, memoryService, orchestrator, httpapi.HandlerConfig{
		Heartbeat: cfg.Chat.Heartbeat,
	})
	healthHandler := httpapi.NewHealthHandler(d.DB, d.Redis)

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
	authorized.Use(auth.Middleware(d.JWT, identityService))
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
