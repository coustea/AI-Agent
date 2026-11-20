// Package api 是组合根：装配所有模块的依赖、注册路由、管理服务生命周期。
//
// 这是唯一知道「所有组件如何拼在一起」的地方：
// 每个模块只声明自己需要什么，由这里提供实现。
package api

import (
	"time"

	"github.com/cloudwego/eino/components/model"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"gorm.io/gorm"

	"mentorly/internal/auth"
	"mentorly/internal/chat"
	"mentorly/internal/config"
	"mentorly/internal/infra"
)

// Deps 是装配所需的全部依赖。
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
	// Chat 需要在退出时等待在途的标题生成任务
	Chat *chat.Service
}

// New 组装中间件、模块与路由表。
func New(d Deps) *App {
	cfg := d.Config
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}

	if cfg.APP.IsProd() {
		gin.SetMode(gin.ReleaseMode)
	}

	// ---------- 存储 ----------
	chatStore := chat.NewStore(d.DB)
	userStore := auth.NewStore(d.DB)
	lock := infra.NewLock(d.Redis)

	// ---------- chat 模块 ----------
	// 未配置模型时 runner 为 nil：对话接口返回 503，其余接口照常可用。
	runner := chat.NewAgentRunner(d.LLM, cfg.Chat.SkillsDir)

	chatSvc := chat.New(chat.Deps{
		Store: chatStore,
		Lock:  lock,
		Agent: runner,
		Log:   log,
		Cfg:   chatConfig(cfg),
	})
	chatHandler := chat.NewHandler(chat.HandlerDeps{
		Service:   chatSvc,
		Heartbeat: cfg.Chat.Heartbeat,
		UserID:    auth.CurrentUserID,
	})

	if runner != nil {
		log.Info("对话能力已启用", zap.String("model", cfg.LLM.Model))
	} else {
		log.Warn("未配置 llm.api_key，AI 能力不可用（/chat 将返回 503）")
	}

	// ---------- auth 模块 ----------
	authSvc := auth.NewService(userStore, d.JWT)
	authHandler := auth.NewHandler(authSvc)

	// ---------- 路由 ----------
	engine := gin.New()
	engine.Use(
		RequestID(),
		Logger(),
		Recovery(),
		CORS(nil),
	)
	engine.NoRoute(NoRoute())

	health := NewHealthHandler(d.DB, d.Redis)
	engine.GET("/healthz", health.Live)
	engine.GET("/readyz", health.Ready)

	v1 := engine.Group("/api/v1")

	// 公开端点
	auth.RegisterPublic(v1, authHandler)

	// 需要登录的端点。
	// 除签名与有效期外，还回查用户是否仍然存在且未被禁用，
	// 使停用/删号能立即失效，而不必等到 token 过期。
	authMW := auth.Middleware(d.JWT, authSvc)
	auth.RegisterProtected(v1, authMW, authHandler)
	chat.Register(v1, authMW, chatHandler)

	return &App{Engine: engine, Chat: chatSvc}
}

// chatConfig 把全局配置拍平成 chat 模块的业务参数。
//
// 模块只接收这个扁平值对象，不 import config 包，
// 因此对配置文件的形状零知识。
func chatConfig(cfg *config.Config) chat.Config {
	return chat.Config{
		WorkspaceDir:            cfg.Chat.WorkspaceDir,
		OffloadDir:              cfg.Chat.OffloadRoot,
		SkillsDir:               cfg.Chat.SkillsDir,
		MaxSteps:                cfg.Chat.MaxSteps,
		RunTimeout:              cfg.Chat.RunTimeout,
		HistoryMaxMessages:      cfg.Chat.HistoryMaxMessages,
		HistoryBudgetTokens:     cfg.Chat.HistoryBudgetTokens,
		CompressTriggerTokens:   cfg.Chat.CompressTriggerTokens,
		CompressTriggerMessages: cfg.Chat.CompressTriggerMessages,
		CompressSourceMaxChars:  cfg.Chat.CompressSourceMaxChars,
		KeepRecentTurns:         cfg.Chat.KeepRecentTurns,
		TitleWorkers:            cfg.Chat.TitleWorkers,
		TitleTimeout:            cfg.Chat.TitleTimeout,
	}
}

// 编译期断言：确保依赖的时间类型未被误改。
var _ = time.Second
