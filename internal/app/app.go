// Package app 是组合根：装配全部模块、注册路由、管理生命周期。
//
// 这是唯一知道「所有组件如何拼在一起」的地方。
// 各模块只声明自己需要什么，由这里提供实现，
// 因此 Agent、Capability、Transport 之间互不 import。
package app

import (
	"context"
	"fmt"
	"time"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"gorm.io/gorm"

	"mentorly/internal/agents/tutor"
	"mentorly/internal/auth"
	"mentorly/internal/capabilities/artifacts"
	"mentorly/internal/capabilities/attachments"
	"mentorly/internal/capabilities/diagram"
	"mentorly/internal/capabilities/memory"
	"mentorly/internal/capabilities/presentation"
	"mentorly/internal/capabilities/search"
	"mentorly/internal/capabilities/video"
	"mentorly/internal/config"
	"mentorly/internal/runtime"
	transport "mentorly/internal/transport/http"
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
	// Jobs 需要在退出时等待在途的生成任务
	Jobs *runtime.JobRunner
	// Titles 需要在退出时等待在途的标题生成
	Titles *TitleWorker
}

// New 组装全部模块与路由。
func New(ctx context.Context, d Deps) (*App, error) {
	cfg := d.Config
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}

	if cfg.APP.IsProd() {
		gin.SetMode(gin.ReleaseMode)
	}

	// ---------- 存储层 ----------
	convStore := tutor.NewStore(d.DB)
	memStore := memory.NewStore(d.DB)

	attStore, err := attachments.NewStore(d.DB, attachments.Config{
		Dir:             cfg.Attachments.Dir,
		MaxBytes:        cfg.Attachments.MaxBytes,
		MaxExtractChars: cfg.Attachments.MaxExtractChars,
	})
	if err != nil {
		return nil, fmt.Errorf("初始化附件存储失败: %w", err)
	}

	artStore, err := artifacts.NewStore(d.DB, cfg.Artifacts.Dir)
	if err != nil {
		return nil, fmt.Errorf("初始化产物存储失败: %w", err)
	}

	// ---------- 异步任务 ----------
	jobs := runtime.NewJobRunner(cfg.Artifacts.JobWorkers, cfg.Artifacts.JobTimeout, log)
	artSvc := artifacts.New(artifacts.Deps{Store: artStore, Jobs: jobs, Log: log})

	// ---------- Capability ----------
	tools, err := buildTools(d, cfg, log, attStore, memStore, artSvc)
	if err != nil {
		jobs.Close(5 * time.Second)
		return nil, err
	}

	// ---------- TutorAgent ----------
	tutorCfg := tutor.Config{
		SkillsDir:              cfg.Chat.SkillsDir,
		MaxSteps:               cfg.Chat.MaxSteps,
		SummaryTriggerTokens:   cfg.Chat.SummaryTriggerTokens,
		SummaryTriggerMessages: cfg.Chat.SummaryTriggerMessages,
		Vision:                 cfg.LLM.Vision,
	}
	agent := tutor.New(d.LLM, tools, tutorCfg, log)
	harness := tutor.NewHarness(tutor.HarnessDeps{
		Store:        convStore,
		Attachments:  attStore,
		Config:       tutorCfg,
		WorkspaceDir: cfg.Chat.WorkspaceDir,
		OffloadDir:   cfg.Chat.OffloadRoot,
		Log:          log,
	})
	tutorRuntime := tutor.NewRuntime(tutor.RuntimeDeps{
		Agent: agent,
		Store: convStore,
		Log:   log,
	})

	// 标题生成器：首轮结束后异步生成会话标题
	titles := NewTitleWorker(TitleDeps{
		Model:   d.LLM,
		Store:   convStore,
		Workers: cfg.Chat.TitleWorkers,
		Timeout: cfg.Chat.TitleTimeout,
		Log:     log,
	})

	if agent.Enabled() {
		log.Info("TutorAgent 已启用",
			zap.String("model", cfg.LLM.Model),
			zap.Int("tools", len(tools)),
			zap.Bool("vision", cfg.LLM.Vision),
		)
	} else {
		log.Warn("未配置 llm.api_key，AI 能力不可用（对话接口将返回 503）")
	}

	// ---------- 认证 ----------
	authSvc := auth.NewService(auth.NewStore(d.DB), d.JWT)
	authHandler := auth.NewHandler(authSvc)

	// ---------- 传输层 ----------
	chatHandler := transport.NewChatHandler(transport.ChatDeps{
		Store:        convStore,
		Harness:      harness,
		Runtime:      tutorRuntime,
		AgentEnabled: agent.Enabled(),
		Titles:       titles,
		Heartbeat:    cfg.Chat.Heartbeat,
		RunTimeout:   cfg.Chat.RunTimeout,
		UserID:       auth.CurrentUserID,
		Log:          log,
	})

	attHandler := transport.NewAttachmentHandler(transport.AttachmentDeps{
		Store:  attStore,
		UserID: auth.CurrentUserID,
	})

	artHandler := transport.NewArtifactHandler(transport.ArtifactDeps{
		Service: artSvc,
		UserID:  auth.CurrentUserID,
	})

	// ---------- 路由 ----------
	engine := gin.New()
	engine.Use(
		transport.RequestID(),
		transport.Logger(log),
		transport.Recovery(log),
		transport.CORS(nil),
	)
	engine.NoRoute(transport.NoRoute())

	health := transport.NewHealthHandler(d.DB)
	engine.GET("/healthz", health.Live)
	engine.GET("/readyz", health.Ready)

	v1 := engine.Group("/api/v1")
	auth.RegisterPublic(v1, authHandler)

	authMW := auth.Middleware(d.JWT, authSvc)
	auth.RegisterProtected(v1, authMW, authHandler)

	chatHandler.Register(v1, authMW)
	attHandler.Register(v1, authMW)
	artHandler.Register(v1, authMW)

	return &App{Engine: engine, Jobs: jobs, Titles: titles}, nil
}

// buildTools 组装全部 Capability 工具。
//
// 工具列表是 Agent 的能力边界：这里注册什么，Agent 就能做什么。
// 未配置的能力不注册（而不是注册一个必然失败的工具），
// 让 Agent 不会尝试调用不可用的功能。
func buildTools(
	d Deps,
	cfg *config.Config,
	log *zap.Logger,
	attStore *attachments.Store,
	memStore *memory.Store,
	artSvc *artifacts.Service,
) ([]tool.BaseTool, error) {
	var tools []tool.BaseTool

	// 记忆：始终可用（依赖 MySQL）
	memTools, err := memory.Tools(memStore)
	if err != nil {
		return nil, fmt.Errorf("装配记忆工具失败: %w", err)
	}
	tools = append(tools, memTools...)

	// 附件：始终可用
	attTools, err := attachments.Tools(attStore)
	if err != nil {
		return nil, fmt.Errorf("装配附件工具失败: %w", err)
	}
	tools = append(tools, attTools...)

	// 产物状态查询
	artTools, err := artifacts.Tools(artSvc)
	if err != nil {
		return nil, fmt.Errorf("装配产物工具失败: %w", err)
	}
	tools = append(tools, artTools...)

	// 图解：纯 Go 生成 SVG，无外部依赖
	diagTool, err := diagram.NewTool(diagram.NewRenderer(artSvc))
	if err != nil {
		return nil, fmt.Errorf("装配图解工具失败: %w", err)
	}
	tools = append(tools, diagTool)

	// 课件：纯 Go 生成 PPTX
	presTool, err := presentation.NewTool(presentation.NewRenderer(artSvc))
	if err != nil {
		return nil, fmt.Errorf("装配课件工具失败: %w", err)
	}
	tools = append(tools, presTool)

	// 视频：需要 ffmpeg 与字体。缺失时明确降级，不注册工具。
	videoRenderer, err := video.NewRenderer(artSvc, video.Config{
		FFmpegPath: cfg.Artifacts.FFmpegPath,
		FontPath:   cfg.Artifacts.FontPath,
		Width:      cfg.Artifacts.VideoWidth,
		Height:     cfg.Artifacts.VideoHeight,
		FPS:        cfg.Artifacts.VideoFPS,
	})
	if err != nil {
		log.Warn("视频生成能力不可用，相关工具不会注册", zap.Error(err))
	} else {
		videoTool, err := video.NewTool(videoRenderer)
		if err != nil {
			return nil, fmt.Errorf("装配视频工具失败: %w", err)
		}
		tools = append(tools, videoTool)
		log.Info("视频生成能力已启用",
			zap.String("ffmpeg", cfg.Artifacts.FFmpegPath),
			zap.Int("width", cfg.Artifacts.VideoWidth),
			zap.Int("height", cfg.Artifacts.VideoHeight),
		)
	}

	// 搜索：可选，未配置不注册
	searcher, err := search.New(search.Config{
		Provider: cfg.Search.Provider,
		APIKey:   cfg.Search.APIKey,
		BaseURL:  cfg.Search.BaseURL,
	})
	if err != nil {
		return nil, fmt.Errorf("装配搜索能力失败: %w", err)
	}
	if searcher != nil {
		searchTools, err := search.Tools(searcher)
		if err != nil {
			return nil, fmt.Errorf("装配搜索工具失败: %w", err)
		}
		tools = append(tools, searchTools...)
		log.Info("联网搜索能力已启用", zap.String("provider", cfg.Search.Provider))
	}

	return tools, nil
}
