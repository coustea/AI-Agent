package tui

import (
	"strings"

	"github.com/charmbracelet/glamour"
)

// renderMarkdown 将 Markdown 文本渲染为适配终端环境的高颜值富文本 (语法高亮、标题上色、表格排版)
func renderMarkdown(content string, width int) string {
	content = strings.TrimSpace(content)
	if content == "" {
		return ""
	}

	wrapWidth := max(36, width)
	r, err := glamour.NewTermRenderer(
		glamour.WithStandardStyle("dark"),
		glamour.WithWordWrap(wrapWidth),
	)
	if err != nil {
		return content
	}

	rendered, err := r.Render(content)
	if err != nil {
		return content
	}

	return strings.TrimSpace(rendered)
}
