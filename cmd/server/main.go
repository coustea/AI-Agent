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
	if err := gotenv.Load(); err != nil {
		fmt.Fprintln(os.Stderr, "未找到 .env 文件，将使用系统环境变量")
	}

	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "加载配置失败: %v\n", err)
		os.Exit(1)
	}

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
	db, err := infra.InitMySQL(cfg.Database.MySQL, lg)
	if err != nil {
		return err
	}
	defer func() { _ = infra.CloseMySQL(db) }()

	models := append([]any{&users.User{}}, conversations.Schema()...)
	models = append(models, attachments.Schema()...)
	if err := infra.AutoMigrate(db, models, lg); err != nil {
		return err
	}

	cm, err := agent.NewModel(context.Background(), agent.ModelConfig{
		Provider: cfg.LLM.Provider,
		Model:    cfg.LLM.Model,
		BaseURL:  cfg.LLM.BaseURL,
		APIKey:   cfg.LLM.APIKey,
		MaxToken: cfg.LLM.MaxToken,
		Timeout:  cfg.LLM.Timeout,
		Extra:    cfg.LLM.ExtraFields,
	})
	if err != nil {
		return fmt.Errorf("初始化模型失败: %w", err)
	}

	if cfg.APP.IsProd() {
		gin.SetMode(gin.ReleaseMode)
	}
	convStore := conversations.NewStore(db)
	attStore, err := attachments.NewStore(db, attachments.Config{
		Dir:             agent.DefaultWorkspaceDir,
		MaxBytes:        cfg.Attachments.MaxBytes,
		MaxExtractChars: cfg.Attachments.MaxExtractChars,
	})
	if err != nil {
		return err
	}

	tutor, err := agent.New(context.Background(), agent.AgentDeps{
		Model:         cm,
		Conversations: convStore,
		Attachments:   attStore,
		Search:        agent.SearchConfig{Provider: cfg.Search.Provider, APIKey: cfg.Search.APIKey, BaseURL: cfg.Search.BaseURL},
		ShellTimeout:  cfg.Chat.ShellTimeout,
		Config: agent.Config{
			ModelProvider: cfg.LLM.Provider,
			ModelExtra:    cfg.LLM.ExtraFields,
			ThinkingMode:  cfg.LLM.ThinkingMode,
			MaxSteps:      cfg.Chat.MaxSteps,
			ContextWindow: cfg.LLM.ContextWindow,
			MaxToken:      cfg.LLM.MaxToken,
		},
		Log: lg,
	})
	if err != nil {
		return err
	}

	harness := agent.NewHarness(agent.DefaultWorkspaceDir, convStore, attStore)
	chatSvc := service.NewChat(convStore, attStore, cfg.Attachments.MaxPerMessage, lg)
	jwt := auth.New(cfg.JWT)
	authSvc := auth.NewService(users.NewStore(db), jwt)

	authHandler := handlers.NewAuthHandler(authSvc)
	chatHandler := handlers.NewChatHandler(handlers.ChatDeps{
		Service:    chatSvc,
		Harness:    harness,
		Agent:      tutor,
		Heartbeat:  cfg.Chat.Heartbeat,
		RunTimeout: cfg.Chat.RunTimeout,
		Log:        lg,
	})
	filesHandler := handlers.NewFilesHandler(
		service.NewAttachments(attStore, convStore),
		service.NewWorkspace(agent.DefaultWorkspaceDir, convStore),
	)
	healthHandler := handlers.NewHealthHandler(func(ctx context.Context) error {
		sqlDB, err := db.DB()
		if err != nil {
			return err
		}
		return sqlDB.PingContext(ctx)
	})

	engine := gin.New()
	engine.Use(middleware.RequestID(), middleware.Logger(lg), middleware.Recovery(lg), middleware.CORS())
	engine.NoRoute(middleware.NoRoute())
	router.Register(engine, middleware.Auth(jwt, authSvc), authHandler, chatHandler, filesHandler, healthHandler)

	srv := &http.Server{
		Addr:              cfg.APP.Addr(),
		Handler:           engine,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       120 * time.Second,
	}

	errCh := make(chan error, 1)
	go func() {
		lg.Info("HTTP 服务启动", zap.String("addr", cfg.APP.Addr()))
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
	}()

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
