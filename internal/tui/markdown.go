package tui

import (
	"strings"
	"sync"

	"github.com/charmbracelet/glamour"
)

var (
	rendererMu    sync.RWMutex
	rendererCache = make(map[int]*glamour.TermRenderer)
)

func getRenderer(width int) (*glamour.TermRenderer, error) {
	rendererMu.RLock()
	r, ok := rendererCache[width]
	rendererMu.RUnlock()
	if ok {
		return r, nil
	}

	rendererMu.Lock()
	defer rendererMu.Unlock()
	if r, ok = rendererCache[width]; ok {
		return r, nil
	}

	newR, err := glamour.NewTermRenderer(
		glamour.WithStandardStyle("dark"),
		glamour.WithWordWrap(width),
	)
	if err != nil {
		return nil, err
	}
	rendererCache[width] = newR
	return newR, nil
}

// renderMarkdown 将 Markdown 文本渲染为适配终端环境的高颜值富文本 (语法高亮、标题上色、表格排版)
func renderMarkdown(content string, width int) string {
	content = strings.TrimSpace(content)
	if content == "" {
		return ""
	}

	wrapWidth := max(36, width)
	r, err := getRenderer(wrapWidth)
	if err != nil {
		return content
	}

	rendered, err := r.Render(content)
	if err != nil {
		return content
	}

	return strings.TrimSpace(rendered)
}
