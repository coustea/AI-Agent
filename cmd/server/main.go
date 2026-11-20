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

	"mentorly/internal/api"
	"mentorly/internal/auth"
	"mentorly/internal/chat"
	"mentorly/internal/config"
	"mentorly/internal/infra"
	"mentorly/internal/log"
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

	// 3. 初始化日志。注意：日志组件依赖配置，所以必须放在配置加载之后。
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

	zap.L().Info("配置加载成功",
		zap.String("app", cfg.APP.Name),
		zap.String("env", cfg.APP.Env),
	)

	if err := run(cfg); err != nil {
		zap.L().Error("服务异常退出", zap.Error(err))
		os.Exit(1)
	}
}

func run(cfg *config.Config) error {
	// 4. 初始化 MySQL
	db, err := infra.InitMySQL(cfg)
	if err != nil {
		return fmt.Errorf("初始化 MySQL 失败: %w", err)
	}
	defer func() { _ = infra.CloseMySQL(db) }()
	zap.L().Info("MySQL 初始化成功", zap.String("database", cfg.Database.MySQL.Database))

	// 5. 自动迁移。各模块自己声明拥有的表，main 不需要知道表结构细节。
	if err := infra.AutoMigrate(db, append(auth.Schema(), chat.Schema()...)...); err != nil {
		return err
	}

	// 6. 初始化 Redis
	rdb, err := infra.InitRedis(cfg)
	if err != nil {
		return fmt.Errorf("初始化 Redis 失败: %w", err)
	}
	defer func() { _ = infra.CloseRedis(rdb) }()
	zap.L().Info("Redis 初始化成功", zap.String("addr", cfg.Database.Redis.Addr))

	// 7. 初始化 eino ChatModel。未配置 key 时返回 nil，服务照常启动。
	ctx := context.Background()
	cm, err := infra.NewModel(ctx, cfg.LLM)
	if err != nil {
		return fmt.Errorf("初始化 LLM 失败: %w", err)
	}

	// 8. 组装路由
	app := api.New(api.Deps{
		Config: cfg,
		DB:     db,
		Redis:  rdb,
		JWT:    auth.New(cfg.JWT),
		LLM:    cm,
		Log:    zap.L(),
	})

	// 退出时等待在途的标题生成任务，最多 10 秒。
	if app.Chat != nil {
		defer app.Chat.Close(10 * time.Second)
	}

	// 9. 启动 HTTP 服务，支持优雅关闭
	addr := cfg.APP.Addr()
	srv := &http.Server{
		Addr:              addr,
		Handler:           app.Engine,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      90 * time.Second,
		IdleTimeout:       120 * time.Second,
	}

	signalCtx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	errCh := make(chan error, 1)
	go func() {
		zap.L().Info("HTTP 服务启动", zap.String("address", addr))
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
	}()

	select {
	case err := <-errCh:
		return fmt.Errorf("HTTP 服务异常: %w", err)
	case <-signalCtx.Done():
		zap.L().Info("收到退出信号，开始优雅关闭")
	}

	// 给在途请求留出处理时间。
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("优雅关闭失败: %w", err)
	}

	zap.L().Info("服务已退出")
	return nil
}
