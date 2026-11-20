// Package logger 提供基于 zap 的日志组件：
// 终端输出带颜色的可读格式，文件输出 JSON 并按日期分目录归档。
package logger

import (
	"io"
	"os"
	"path/filepath"
	"sync"
	"time"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Options 控制日志组件的输出行为。
type Options struct {
	// Dir 日志根目录，每天一个子目录
	Dir string
	// Level debug / info / warn / error
	Level string
	// MaxSize 单文件最大体积（MB）
	MaxSize int
	// MaxBackup 每个日期目录保留的备份数
	MaxBackup int
	// Compress 是否压缩历史备份
	Compress bool
}

// dailyWriter 按日期切换日志目录，跨天时自动新建文件。
type dailyWriter struct {
	mu      sync.Mutex
	dir     string
	day     string
	current *lumberjack.Logger

	maxSize   int
	maxBackup int
	compress  bool
}

func (w *dailyWriter) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	today := time.Now().Format("2006-01-02")

	// 日期变化时，创建新的日志目录与文件
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

// Close 关闭当前文件句柄，供进程退出前调用。
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

	// 终端：带颜色的可读格式
	consoleCfg := zap.NewDevelopmentEncoderConfig()
	consoleCfg.EncodeTime = zapcore.ISO8601TimeEncoder
	consoleCfg.EncodeLevel = zapcore.CapitalColorLevelEncoder

	consoleCore := zapcore.NewCore(
		zapcore.NewConsoleEncoder(consoleCfg),
		zapcore.AddSync(os.Stdout),
		level,
	)

	// 文件：JSON 格式，便于后续采集
	fileCfg := zap.NewProductionEncoderConfig()
	fileCfg.EncodeTime = zapcore.ISO8601TimeEncoder

	fileCore := zapcore.NewCore(
		zapcore.NewJSONEncoder(fileCfg),
		zapcore.AddSync(writer),
		level,
	)

	log := zap.New(
		zapcore.NewTee(consoleCore, fileCore),
		zap.AddCaller(),
		zap.AddStacktrace(zap.ErrorLevel),
	)

	return log, writer, nil
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
