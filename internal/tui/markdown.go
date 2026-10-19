package tui

import (
	"encoding/binary"
	"hash/fnv"
	"strings"
	"sync"

	"github.com/charmbracelet/glamour"
)

var (
	rendererMu    sync.RWMutex
	rendererCache = make(map[int]*glamour.TermRenderer)

	// 块级渲染缓存：key = FNV64(内容 + 宽度)。
	// 已完成的历史块内容不再变化，命中后无需重复 glamour 渲染；
	// 流式中的当前块内容每帧变化，由调用方走 renderMarkdown 不入缓存。
	mdCacheMu sync.RWMutex
	mdCache   = make(map[uint64]string)
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

// renderMarkdownCached 渲染已完成的历史块，命中缓存则直接复用。
func renderMarkdownCached(content string, width int) string {
	content = strings.TrimSpace(content)
	if content == "" {
		return ""
	}

	key := mdCacheKey(content, width)
	mdCacheMu.RLock()
	if v, ok := mdCache[key]; ok {
		mdCacheMu.RUnlock()
		return v
	}
	mdCacheMu.RUnlock()

	out := renderMarkdown(content, width)

	mdCacheMu.Lock()
	mdCache[key] = out
	mdCacheMu.Unlock()
	return out
}

func mdCacheKey(content string, width int) uint64 {
	h := fnv.New64a()
	_, _ = h.Write([]byte(content))
	_, _ = h.Write([]byte{0})
	var buf [4]byte
	binary.LittleEndian.PutUint32(buf[:], uint32(width))
	_, _ = h.Write(buf[:])
	return h.Sum64()
}
