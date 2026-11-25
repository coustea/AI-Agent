package log

import (
	"context"
	"go.uber.org/zap"
	"regexp"
	"strings"
)

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

// Content 只做凭据脱敏与明确截断，不改写模型或工具输出。
func Content(key, value string) zap.Field {
	value = credentials.ReplaceAllString(value, "${1}[REDACTED]")
	const limit = 16000
	runes := []rune(value)
	if len(runes) > limit {
		value = string(runes[:limit]) + "\n[日志已截断]"
	}
	// 保留换行，移除终端控制符，避免工具输出操纵终端。
	value = strings.Map(func(r rune) rune {
		if r < 32 && r != '\n' && r != '\t' {
			return -1
		}
		return r
	}, value)
	return zap.String(key, value)
}
