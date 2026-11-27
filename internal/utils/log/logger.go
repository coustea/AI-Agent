// Package log 提供基于 zap 的日志组件：
// 终端输出带颜色的可读格式，文件输出 JSON 并按日期分目录归档，支持上下文传递与凭据脱敏。
package log

import (
	"context"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"

	"mentorly/internal/utils"
)

type Options struct {
	Dir       string
	Level     string
	MaxSize   int
	MaxBackup int
	Compress  bool
}

type dailyWriter struct {
	mu        sync.Mutex
	dir       string
	day       string
	current   *lumberjack.Logger
	maxSize   int
	maxBackup int
	compress  bool
}

func (w *dailyWriter) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	today := time.Now().Format("2006-01-02")
	if today != w.day {
		dir := filepath.Join(w.dir, today)
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return 0, err
		}
		if w.current != nil {
			if err := w.current.Close(); err != nil {
				return 0, err
			}
		}
		w.current = &lumberjack.Logger{
			Filename:   filepath.Join(dir, "app.log"),
			MaxSize:    w.maxSize,
			MaxBackups: w.maxBackup,
			Compress:   w.compress,
			LocalTime:  true,
		}
		w.day = today
	}
	return w.current.Write(p)
}

func (w *dailyWriter) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.current != nil {
		return w.current.Close()
	}
	return nil
}

// Init 初始化 zap，返回 Logger 与文件关闭器（退出前需调用 Close）。
func Init(opt Options) (*zap.Logger, io.Closer, error) {
	if opt.Dir == "" {
		opt.Dir = "logs"
	}
	if opt.MaxSize <= 0 {
		opt.MaxSize = 50
	}
	if opt.MaxBackup <= 0 {
		opt.MaxBackup = 5
	}
	if err := os.MkdirAll(opt.Dir, 0o755); err != nil {
		return nil, nil, err
	}

	writer := &dailyWriter{
		dir:       opt.Dir,
		maxSize:   opt.MaxSize,
		maxBackup: opt.MaxBackup,
		compress:  opt.Compress,
	}
	level := parseLevel(opt.Level)

	consoleCfg := zap.NewDevelopmentEncoderConfig()
	consoleCfg.EncodeTime = zapcore.ISO8601TimeEncoder
	consoleCfg.EncodeLevel = zapcore.CapitalColorLevelEncoder
	consoleCore := zapcore.NewCore(zapcore.NewConsoleEncoder(consoleCfg), zapcore.AddSync(os.Stdout), level)

	fileCfg := zap.NewProductionEncoderConfig()
	fileCfg.EncodeTime = zapcore.ISO8601TimeEncoder
	fileCore := zapcore.NewCore(zapcore.NewJSONEncoder(fileCfg), zapcore.AddSync(writer), level)

	lg := zap.New(
		zapcore.NewTee(consoleCore, fileCore),
		zap.AddCaller(),
		zap.AddStacktrace(zap.ErrorLevel),
	)
	return lg, writer, nil
}

func parseLevel(level string) zapcore.Level {
	switch level {
	case "debug":
		return zap.DebugLevel
	case "warn", "warning":
		return zap.WarnLevel
	case "error":
		return zap.ErrorLevel
	default:
		return zap.InfoLevel
	}
}

type contextKey struct{}

func WithContext(ctx context.Context, logger *zap.Logger) context.Context {
	return context.WithValue(ctx, contextKey{}, logger)
}

func FromContext(ctx context.Context, fallback *zap.Logger) *zap.Logger {
	if logger, ok := ctx.Value(contextKey{}).(*zap.Logger); ok && logger != nil {
		return logger
	}
	if fallback != nil {
		return fallback
	}
	return zap.NewNop()
}

var credentials = regexp.MustCompile(`(?i)((?:api[_-]?key|access[_-]?token|authorization|password|secret)["']?\s*[:=]\s*["']?)(?:Bearer\s+)?[^\s"',}]+`)

// Content 只做凭据脱敏、截断与控制符清理，不改写业务输出。
func Content(key, value string) zap.Field {
	value = credentials.ReplaceAllString(value, "${1}[REDACTED]")
	const limit = 16000
	if clipped := utils.ClipRunes(value, limit); len(clipped) < len(value) {
		value = clipped + "\n[日志已截断]"
	}
	value = strings.Map(func(r rune) rune {
		if r < 32 && r != '\n' && r != '\t' {
			return -1
		}
		return r
	}, value)
	return zap.String(key, value)
}
