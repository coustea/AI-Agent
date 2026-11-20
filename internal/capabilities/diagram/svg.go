package diagram

import (
	"fmt"
	"html"
	"math"
	"strings"
)

// 画布与排版常量。
//
// 配色沿用 skills/diagram/SKILL.md 的规范：单一主色 + 灰阶，
// 避免默认随机彩色让图看起来像草稿。
const (
	padding       = 40.0
	nodeHeight    = 56.0
	nodeMinW      = 120.0
	nodeGapX      = 60.0
	nodeGapY      = 76.0
	perRowMax     = 4
	fontFamily    = "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
	colorPrimary  = "#2F6FEB"
	colorPrimaryD = "#1E4FBF"
	colorAlt      = "#6B7280"
	colorText     = "#111827"
	colorBG       = "#FFFFFF"
	colorPanel    = "#F9FAFB"
	colorBorder   = "#E5E7EB"
)

// svg 是渲染中间结果，便于在 render 里分段拼装。
type svg struct {
	b strings.Builder
}

func (s *svg) line(format string, args ...any) {
	fmt.Fprintf(&s.b, format, args...)
	s.b.WriteByte('\n')
}

// render 把内部图渲染成完整 SVG 文档。
func (g *graph) render(title string) (string, error) {
	if len(g.nodes) == 0 {
		return "", fmt.Errorf("图解没有任何节点")
	}

	g.layout()

	width, height := g.bounds()
	s := &svg{}
	s.line(`<?xml version="1.0" encoding="UTF-8"?>`)
	s.line(`<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" viewBox="0 0 %.0f %.0f" font-family="%s">`,
		width, height, width, height, fontFamily)
	s.line(`<defs>`)
	s.line(`<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">`)
	s.line(`<path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/>`, colorAlt)
	s.line(`</marker>`)
	s.line(`</defs>`)
	s.line(`<rect width="100%%" height="100%%" fill="%s"/>`, colorBG)

	// 标题
	if strings.TrimSpace(title) != "" {
		s.line(`<text x="%.0f" y="34" font-size="19" font-weight="600" fill="%s">%s</text>`,
			padding, colorText, html.EscapeString(title))
	}

	// 连线先画，保证节点覆盖在线之上，视觉更干净。
	for _, e := range g.edges {
		g.drawEdge(s, e)
	}
	for _, n := range g.nodes {
		g.drawNode(s, n)
	}

	s.line(`</svg>`)
	return s.b.String(), nil
}

// layout 计算节点位置。
//
// 采用分层网格布局：有向边决定层级，同层节点横向排列。
// 这是刻意选择的简单方案——教学图解通常不超过 15 个节点，
// 引入完整的图布局算法（如力导向）收益很小，却会带来不可预测的排版。
func (g *graph) layout() {
	for _, n := range g.nodes {
		n.w = math.Max(nodeMinW, float64(displayWidth(n.label))*8.6+36)
		n.h = nodeHeight
	}

	levels := g.computeLevels()

	// 按层分组，保持声明顺序，避免同一份输入两次渲染结果不同。
	byLevel := make(map[int][]*node)
	var maxLevel int
	for _, n := range g.nodes {
		lv := levels[n.id]
		byLevel[lv] = append(byLevel[lv], n)
		if lv > maxLevel {
			maxLevel = lv
		}
	}

	// 每层最多 perRowMax 个节点，超出则在本层内折行。
	y := padding + 50
	for lv := 0; lv <= maxLevel; lv++ {
		row := byLevel[lv]
		if len(row) == 0 {
			continue
		}
		rows := chunk(row, perRowMax)
		for _, r := range rows {
			totalW := 0.0
			for i, n := range r {
				if i > 0 {
					totalW += nodeGapX
				}
				totalW += n.w
			}
			x := padding
			// 单行时按画布宽度居中，视觉更稳。
			if len(rows) == 1 {
				if c := g.canvasWidth(); c > totalW {
					x = (c - totalW) / 2
					if x < padding {
						x = padding
					}
				}
			}
			for _, n := range r {
				n.x = x
				n.y = y
				x += n.w + nodeGapX
			}
			y += nodeHeight + nodeGapY
		}
	}
}

// computeLevels 用最长路径法分层：节点层级 = 入边源层级最大值 + 1。
// 对环做保护，避免无限递归。
func (g *graph) computeLevels() map[string]int {
	indeg := make(map[string]int, len(g.nodes))
	adj := make(map[string][]string, len(g.nodes))
	for _, n := range g.nodes {
		indeg[n.id] = 0
	}
	for _, e := range g.edges {
		adj[e.from] = append(adj[e.from], e.to)
		indeg[e.to]++
	}

	levels := make(map[string]int, len(g.nodes))
	queue := make([]string, 0, len(g.nodes))
	for _, n := range g.nodes {
		if indeg[n.id] == 0 {
			queue = append(queue, n.id)
			levels[n.id] = 0
		}
	}

	// 全是环（没有入度为 0 的节点）时退化为按声明顺序分层。
	if len(queue) == 0 {
		for _, n := range g.nodes {
			levels[n.id] = 0
		}
		return levels
	}

	visited := 0
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		visited++
		for _, next := range adj[cur] {
			if lv := levels[cur] + 1; lv > levels[next] {
				levels[next] = lv
			}
			indeg[next]--
			if indeg[next] == 0 {
				queue = append(queue, next)
			}
		}
	}

	// 环上的节点不会被访问到，单独放在最后一层。
	if visited < len(g.nodes) {
		maxLv := 0
		for _, lv := range levels {
			if lv > maxLv {
				maxLv = lv
			}
		}
		for _, n := range g.nodes {
			if _, ok := levels[n.id]; !ok {
				levels[n.id] = maxLv + 1
			}
		}
	}

	return levels
}

// canvasWidth 估算画布宽度，用于单行居中。
func (g *graph) canvasWidth() float64 {
	w := 0.0
	for _, n := range g.nodes {
		if n.w > w {
			w = n.w
		}
	}
	return math.Max(w+padding*2, 520)
}

// bounds 计算画布尺寸，包含全部节点与边标签的余量。
func (g *graph) bounds() (float64, float64) {
	maxX, maxY := 0.0, 0.0
	for _, n := range g.nodes {
		if n.x+n.w > maxX {
			maxX = n.x + n.w
		}
		if n.y+n.h > maxY {
			maxY = n.y + n.h
		}
	}
	w := math.Max(maxX+padding, 480)
	h := math.Max(maxY+padding, 240)
	return w, h
}

// drawNode 绘制一个节点。
func (g *graph) drawNode(s *svg, n *node) {
	fill := colorPanel
	stroke := colorBorder
	textColor := colorText

	// 入口与出口用主色强调，其余保持中性，避免整张图都在喊。
	if len(g.incoming(n.id)) == 0 {
		fill, stroke, textColor = colorPrimary, colorPrimaryD, "#FFFFFF"
	}

	switch n.shape {
	case shapeDiamond:
		cx, cy := n.x+n.w/2, n.y+n.h/2
		s.line(`<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" stroke="%s" stroke-width="1.5"/>`,
			cx, n.y, n.x+n.w, cy, cx, n.y+n.h, n.x, cy, fill, stroke)
	case shapeRound:
		s.line(`<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s" stroke="%s" stroke-width="1.5"/>`,
			n.x, n.y, n.w, n.h, n.h/2, fill, stroke)
	case shapeCylinder:
		s.line(`<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6" fill="%s" stroke="%s" stroke-width="1.5"/>`,
			n.x, n.y, n.w, n.h, fill, stroke)
		// 圆柱顶盖：一条椭圆弧暗示「存储」
		s.line(`<path d="M %.1f %.1f Q %.1f %.1f %.1f %.1f" fill="none" stroke="%s" stroke-width="1.5"/>`,
			n.x, n.y+10, n.x+n.w/2, n.y-6, n.x+n.w, n.y+10, stroke)
	default:
		s.line(`<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="8" fill="%s" stroke="%s" stroke-width="1.5"/>`,
			n.x, n.y, n.w, n.h, fill, stroke)
	}

	lines := wrapLabel(n.label, int((n.w-24)/8.6))
	lineH := 17.0
	startY := n.y + n.h/2 - float64(len(lines)-1)*lineH/2 + 5
	for i, ln := range lines {
		s.line(`<text x="%.1f" y="%.1f" font-size="14" text-anchor="middle" fill="%s">%s</text>`,
			n.x+n.w/2, startY+float64(i)*lineH, textColor, html.EscapeString(ln))
	}
}

// drawEdge 绘制一条连线，带箭头与可选标签。
func (g *graph) drawEdge(s *svg, e *edge) {
	from, ok1 := g.byID[e.from]
	to, ok2 := g.byID[e.to]
	if !ok1 || !ok2 {
		return
	}

	x1, y1 := from.x+from.w/2, from.y+from.h
	x2, y2 := to.x+to.w/2, to.y

	// 同层或反向连接时从侧面出线，避免穿过节点。
	if math.Abs(y2-y1) < 1 || y2 < y1 {
		if x1 < x2 {
			x1, y1 = from.x+from.w, from.y+from.h/2
			x2, y2 = to.x, to.y+to.h/2
		} else {
			x1, y1 = from.x, from.y+from.h/2
			x2, y2 = to.x+to.w, to.y+to.h/2
		}
	}

	dash := ""
	if e.dashed {
		dash = ` stroke-dasharray="5 4"`
	}

	// 用三次贝塞尔让连线自然弯曲，而不是生硬的折线。
	cy := (y1 + y2) / 2
	s.line(`<path d="M %.1f %.1f C %.1f %.1f, %.1f %.1f, %.1f %.1f" fill="none" stroke="%s" stroke-width="1.6"%s marker-end="url(#arrow)"/>`,
		x1, y1, x1, cy, x2, cy, x2, y2, colorAlt, dash)

	if e.label != "" {
		mx, my := (x1+x2)/2, (y1+y2)/2
		w := float64(displayWidth(e.label))*7.2 + 12
		s.line(`<rect x="%.1f" y="%.1f" width="%.1f" height="18" rx="4" fill="%s" stroke="%s"/>`,
			mx-w/2, my-9, w, colorBG, colorBorder)
		s.line(`<text x="%.1f" y="%.1f" font-size="12" text-anchor="middle" fill="%s">%s</text>`,
			mx, my+4, colorAlt, html.EscapeString(e.label))
	}
}

// incoming 返回指向 id 的所有边。
func (g *graph) incoming(id string) []*edge {
	var out []*edge
	for _, e := range g.edges {
		if e.to == id {
			out = append(out, e)
		}
	}
	return out
}

// wrapLabel 按估算宽度折行。
//
// 中文没有空格，因此按 rune 逐个累加宽度，
// 只在超宽时断行，不追求排版完美。
func wrapLabel(label string, maxRunes int) []string {
	if maxRunes < 4 {
		maxRunes = 4
	}
	label = strings.TrimSpace(label)
	if label == "" {
		return []string{""}
	}

	// 标签内的显式换行（来自 <br/>）优先于自动折行。
	if strings.Contains(label, "\n") {
		var out []string
		for _, seg := range strings.Split(label, "\n") {
			out = append(out, wrapLabel(seg, maxRunes)...)
		}
		if len(out) > 3 {
			out = out[:3]
			out[2] = strings.TrimSuffix(out[2], "…") + "…"
		}
		return out
	}

	var out []string
	var cur []rune
	curW := 0.0
	for _, r := range label {
		w := runeWidth(r)
		if curW+w > float64(maxRunes)*1.0 && len(cur) > 0 {
			out = append(out, string(cur))
			cur = cur[:0]
			curW = 0
		}
		cur = append(cur, r)
		curW += w
	}
	if len(cur) > 0 {
		out = append(out, string(cur))
	}
	if len(out) > 3 {
		// 节点内最多三行，超出用省略号，避免文字溢出边框。
		out = out[:3]
		out[2] = strings.TrimSuffix(out[2], "…") + "…"
	}
	return out
}

// displayWidth 估算字符串显示宽度：CJK 计 2，ASCII 计 1。
func displayWidth(s string) float64 {
	w := 0.0
	for _, r := range s {
		w += runeWidth(r)
	}
	return w
}

func runeWidth(r rune) float64 {
	if r < 0x1100 {
		return 1
	}
	// 常见 CJK 区段按双宽处理。
	if (r >= 0x1100 && r <= 0x115F) ||
		(r >= 0x2E80 && r <= 0xA4CF) ||
		(r >= 0xAC00 && r <= 0xD7A3) ||
		(r >= 0xF900 && r <= 0xFAFF) ||
		(r >= 0xFE30 && r <= 0xFE6F) ||
		(r >= 0xFF00 && r <= 0xFF60) ||
		(r >= 0xFFE0 && r <= 0xFFE6) {
		return 2
	}
	return 1
}

func chunk(nodes []*node, size int) [][]*node {
	if size <= 0 {
		return [][]*node{nodes}
	}
	var out [][]*node
	for i := 0; i < len(nodes); i += size {
		end := i + size
		if end > len(nodes) {
			end = len(nodes)
		}
		out = append(out, nodes[i:end])
	}
	return out
}
