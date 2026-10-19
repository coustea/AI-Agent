package middleware

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"unicode/utf8"

	"my-agent/internal/tool"
	"my-agent/pkg/llm"
)

const (
	toolResultBudgetRunes  = 8000 // 单条工具结果落盘阈值（字符数）
	toolResultPreviewRunes = 2000 // 落盘后保留的预览字符数
)

// LargeResultSpill 返回一个 PostToolUse 钩子：工具输出超过阈值时全量落盘，
// 并把结果改写为"前缀预览 + 完整路径提示"，既防止单条大输出打爆模型上下文，
// 又保留模型通过 read_file 回读全量内容的能力。
//
// 落盘属于存储策略，不内嵌在 Agent 内核中；宿主按需挂载。
func LargeResultSpill(workDir string) tool.PostToolUse {
	dir := strings.TrimSpace(workDir)
	if dir == "" {
		dir = "."
	}

	return func(ctx context.Context, call llm.ToolCall, res *llm.ToolResult) {
		if res == nil || res.Content == "" {
			return
		}

		totalRunes := utf8.RuneCountInString(res.Content)
		if totalRunes <= toolResultBudgetRunes {
			return
		}

		resultsDir := filepath.Join(dir, ".tide", "tool-results")
		if err := os.MkdirAll(resultsDir, 0o755); err != nil {
			return // 目录创建失败则降级原样返回
		}

		safeCallID := sanitizeFileName(call.ID)
		if safeCallID == "" {
			safeCallID = "result"
		}
		fileName := fmt.Sprintf("%s.txt", safeCallID)
		fullPath := filepath.Join(resultsDir, fileName)

		// 同名冲突追加数字后缀
		for i := 1; ; i++ {
			if _, err := os.Stat(fullPath); os.IsNotExist(err) {
				break
			}
			fileName = fmt.Sprintf("%s_%d.txt", safeCallID, i)
			fullPath = filepath.Join(resultsDir, fileName)
		}

		if err := os.WriteFile(fullPath, []byte(res.Content), 0o600); err != nil {
			return // 写入失败降级保留原文本，不丢弃信息
		}

		preview := string([]rune(res.Content)[:toolResultPreviewRunes])

		relPath, err := filepath.Rel(dir, fullPath)
		if err != nil {
			relPath = fullPath
		}

		res.Content = fmt.Sprintf("%s\n\n... [output truncated: %d characters total; full content saved to %s — use read_file to view]", preview, totalRunes, filepath.ToSlash(relPath))
	}
}

func sanitizeFileName(name string) string {
	clean := strings.TrimSpace(name)
	replacer := strings.NewReplacer("/", "_", "\\", "_", ":", "_", "*", "_", "?", "_", "\"", "_", "<", "_", ">", "_", "|", "_")
	return replacer.Replace(clean)
}
