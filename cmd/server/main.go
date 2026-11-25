package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/subosito/gotenv"
	"go.uber.org/zap"

	"mentorly/internal/agent"
	"mentorly/internal/agent/tools"
	"mentorly/internal/config"
	"mentorly/internal/handlers"
	"mentorly/internal/middleware"
	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
	"mentorly/internal/repository/infra"
	"mentorly/internal/repository/users"
	"mentorly/internal/router"
	"mentorly/internal/service"
	"mentorly/internal/service/auth"
	"mentorly/internal/utils/log"
)

func main() {
	// 加载 .env（不存在也继续，使用系统环境变量）
	if err := gotenv.Load(); err != nil {
		fmt.Fprintln(os.Stderr, "未找到 .env 文件，将使用系统环境变量")
	}

	// 加载配置。配置有问题必须立刻退出，不能带病启动。
	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "加载配置失败: %v\n", err)
		os.Exit(1)
	}

	// 初始化日志。日志依赖配置，因此必须在配置之后。
	lg, closer, err := log.Init(log.Options{
		Dir:       cfg.Log.Dir,
		Level:     cfg.Log.Level,
		MaxSize:   cfg.Log.MaxSize,
		MaxBackup: cfg.Log.MaxBackup,
		Compress:  cfg.Log.Compress,
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "初始化日志组件失败: %v\n", err)
		os.Exit(1)
	}
	defer func() {
		_ = lg.Sync()
		_ = closer.Close()
	}()
	zap.ReplaceGlobals(lg)

	lg.Info("配置加载成功",
		zap.String("app", cfg.APP.Name),
		zap.String("env", cfg.APP.Env),
	)

	if err := run(cfg, lg); err != nil {
		lg.Error("服务运行失败", zap.Error(err))
		_ = lg.Sync()
		os.Exit(1)
	}
}

func run(cfg *config.Config, lg *zap.Logger) error {
	// 连接 MySQL（硬依赖）
	db, err := infra.InitMySQL(cfg.Database.MySQL, lg)
	if err != nil {
		return err
	}
	defer func() { _ = infra.CloseMySQL(db) }()

	// 新数据库建表；启动过程不执行旧数据迁移或删表。
	models := []any{&users.User{}}
	models = append(models, conversations.Schema()...)
	models = append(models, attachments.Schema()...)

	if err := infra.AutoMigrate(db, models, lg); err != nil {
		return err
	}

	// 装配模型。未配置 api_key 时返回 nil，AI 能力关闭但不阻塞启动。
	cm, err := agent.NewModel(context.Background(), agent.ModelConfig{
		Provider: cfg.LLM.Provider,
		Model:    cfg.LLM.Model,
		BaseURL:  cfg.LLM.BaseURL,
		APIKey:   cfg.LLM.APIKey,
		MaxToken: cfg.LLM.MaxToken,
		Timeout:  int64(cfg.LLM.Timeout.Seconds()),
		Extra:    cfg.LLM.ExtraFields,
	})
	if err != nil {
		return fmt.Errorf("初始化模型失败: %w", err)
	}

	// 装配仓储、Agent、业务服务和 HTTP 路由。
	if cfg.APP.IsProd() {
		gin.SetMode(gin.ReleaseMode)
	}
	convStore := conversations.NewStore(db)
	attStore, err := attachments.NewStore(db, attachments.Config{Dir: agent.DefaultWorkspaceDir, MaxBytes: cfg.Attachments.MaxBytes, MaxExtractChars: cfg.Attachments.MaxExtractChars})
	if err != nil {
		return err
	}
	agentCfg := agent.Config{
		ModelProvider: cfg.LLM.Provider, ModelExtra: cfg.LLM.ExtraFields,
		MaxSteps: cfg.Chat.MaxSteps, HistoryToolTurns: cfg.Chat.HistoryToolTurns,
		ReduceTriggerTokens: cfg.Chat.ReduceTriggerTokens, SummaryTriggerTokens: cfg.Chat.SummaryTriggerTokens,
		SummaryTriggerMessages: cfg.Chat.SummaryTriggerMessages,
	}
	agentTools, searchEnabled, err := tools.Build(tools.Config{
		Attachments:    attStore,
		Conversations:  convStore,
		MountWorkspace: agent.MountWorkspace,
		Principal:      agent.PrincipalIDs,
		Shell: tools.ShellConfig{
			Timeout:     cfg.Chat.ShellTimeout,
			SkillsDir:   agent.DefaultSkillsDir,
			WorkspaceOf: agent.WorkspaceDir,
		},
		Search: tools.SearchConfig{Provider: cfg.Search.Provider, APIKey: cfg.Search.APIKey, BaseURL: cfg.Search.BaseURL},
	})
	if err != nil {
		return err
	}
	if searchEnabled {
		lg.Info("联网搜索能力已启用", zap.String("provider", cfg.Search.Provider))
	}
	tutor, err := agent.New(context.Background(), agent.AgentDeps{Model: cm, Tools: agentTools, Config: agentCfg, Log: lg})
	if err != nil {
		return err
	}
	harness := agent.NewHarness(agent.HarnessDeps{Attachments: attStore, Conversations: convStore, Config: agentCfg})
	chat := service.NewChat(convStore, attStore, cfg.Attachments.MaxPerMessage, lg)

	jwt := auth.New(cfg.JWT)
	authService := auth.NewService(users.NewStore(db), jwt)
	authHandler := handlers.NewAuthHandler(authService)
	chatHandler := handlers.NewChatHandler(handlers.ChatDeps{Service: chat, Harness: harness, Agent: tutor, Heartbeat: cfg.Chat.Heartbeat, RunTimeout: cfg.Chat.RunTimeout, Log: lg})
	fileHandler := handlers.NewFileHandler(service.NewAttachments(attStore, convStore))
	workspaceHandler := handlers.NewWorkspaceHandler(service.NewWorkspace(agent.DefaultWorkspaceDir, convStore))
	healthHandler := handlers.NewHealthHandler(func(ctx context.Context) error {
		sqlDB, err := db.DB()
		if err != nil {
			return err
		}
		return sqlDB.PingContext(ctx)
	})

	engine := gin.New()
	engine.Use(middleware.RequestID(), middleware.Logger(lg), middleware.Recovery(lg), middleware.CORS(nil))
	engine.NoRoute(middleware.NoRoute())
	router.Register(engine, middleware.Auth(jwt, authService), authHandler, chatHandler, fileHandler, workspaceHandler, healthHandler)
	// 启动 HTTP 服务
	srv := &http.Server{
		Addr:              cfg.APP.Addr(),
		Handler:           engine,
		ReadHeaderTimeout: 10 * time.Second,
		// 不设 WriteTimeout：SSE 长连接会被它强制中断。
		// 单轮超时由 chat.run_timeout 在业务层控制。
		IdleTimeout: 120 * time.Second,
	}

	errCh := make(chan error, 1)
	go func() {
		lg.Info("HTTP 服务启动", zap.String("addr", cfg.APP.Addr()))
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
	}()

	// 优雅退出
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	select {
	case err := <-errCh:
		return fmt.Errorf("HTTP 服务异常退出: %w", err)
	case sig := <-quit:
		lg.Info("收到退出信号，开始优雅关闭", zap.String("signal", sig.String()))
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		lg.Warn("HTTP 服务关闭超时", zap.Error(err))
	}

	lg.Info("服务已退出")
	return nil
}
