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

	"github.com/subosito/gotenv"
	"go.uber.org/zap"

	"mentorly/internal/agents/tutor"
	"mentorly/internal/app"
	"mentorly/internal/auth"
	"mentorly/internal/capabilities/artifacts"
	"mentorly/internal/capabilities/attachments"
	"mentorly/internal/capabilities/memory"
	"mentorly/internal/config"
	"mentorly/internal/infra"
	"mentorly/internal/log"
	"mentorly/internal/runtime"
)

func main() {
	// 1. 加载 .env（不存在也继续，使用系统环境变量）
	if err := gotenv.Load(); err != nil {
		fmt.Fprintln(os.Stderr, "未找到 .env 文件，将使用系统环境变量")
	}

	// 2. 加载配置。配置有问题必须立刻退出，不能带病启动。
	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "加载配置失败: %v\n", err)
		os.Exit(1)
	}

	// 3. 初始化日志。日志依赖配置，因此必须在配置之后。
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
	// 4. 连接 MySQL（硬依赖）
	db, err := infra.InitMySQL(cfg.Database.MySQL, lg)
	if err != nil {
		return err
	}
	defer func() { _ = infra.CloseMySQL(db) }()

	// 5. 连接 Redis（软依赖，失败降级为 nil）
	rdb, err := infra.InitRedis(cfg.Database.Redis, lg)
	if err != nil {
		return err
	}
	defer func() { _ = infra.CloseRedis(rdb) }()

	// 6. 建表。破坏性变更不在此处执行，见 migrations/。
	models := []any{}
	models = append(models, auth.Schema()...)
	models = append(models, tutor.NewStore(db).Schema()...)
	models = append(models, memory.NewStore(db).Schema()...)
	models = append(models, (&attachments.Store{}).Schema()...)
	models = append(models, (&artifacts.Store{}).Schema()...)

	if err := infra.AutoMigrate(db, models, lg); err != nil {
		return err
	}

	// 7. 装配模型。未配置 api_key 时返回 nil，AI 能力关闭但不阻塞启动。
	cm, err := runtime.NewModel(context.Background(), runtime.ModelConfig{
		Provider: cfg.LLM.Provider,
		Model:    cfg.LLM.Model,
		BaseURL:  cfg.LLM.BaseURL,
		APIKey:   cfg.LLM.APIKey,
		MaxToken: cfg.LLM.MaxToken,
		Timeout:  int64(cfg.LLM.Timeout.Seconds()),
		Extra:    cfg.LLM.ExtraFields,
		Vision:   cfg.LLM.Vision,
	})
	if err != nil {
		return fmt.Errorf("初始化模型失败: %w", err)
	}

	// 8. 装配应用
	application, err := app.New(context.Background(), app.Deps{
		Config: cfg,
		DB:     db,
		JWT:    auth.New(cfg.JWT),
		LLM:    cm,
		Log:    lg,
	})
	if err != nil {
		return err
	}

	// 9. 启动 HTTP 服务
	srv := &http.Server{
		Addr:              cfg.APP.Addr(),
		Handler:           application.Engine,
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

	// 10. 优雅退出
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	select {
	case err := <-errCh:
		application.Jobs.Close(5 * time.Second)
		application.Titles.Close(5 * time.Second)
		return fmt.Errorf("HTTP 服务异常退出: %w", err)
	case sig := <-quit:
		lg.Info("收到退出信号，开始优雅关闭", zap.String("signal", sig.String()))
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		lg.Warn("HTTP 服务关闭超时", zap.Error(err))
	}

	// 等待在途的异步任务收尾，避免产物生成到一半被强杀。
	application.Jobs.Close(10 * time.Second)
	application.Titles.Close(5 * time.Second)

	lg.Info("服务已退出")
	return nil
}
