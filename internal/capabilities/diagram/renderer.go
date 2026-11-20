package diagram

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"mentorly/internal/capabilities/artifacts"
)

// Spec 是图解生成规格。
//
// Mermaid 是模型最擅长书写的图描述语言，因此以它为主要输入；
// 同时支持直接给结构化的节点与连线，避免所有图都挤在 Mermaid 一条路上。
type Spec struct {
	// Title 图解标题
	Title string `json:"title"`
	// Kind 图类型：flow / sequence / state / er / mindmap
	Kind string `json:"kind"`
	// Mermaid 原始 Mermaid 源码。给出时优先使用。
	Mermaid string `json:"mermaid"`
	// Nodes / Edges 结构化输入，Mermaid 为空时使用
	Nodes []Node `json:"nodes,omitempty"`
	Edges []Edge `json:"edges,omitempty"`
}

// Node 是结构化图的一个节点。
type Node struct {
	ID    string `json:"id"`
	Label string `json:"label"`
	// Shape box / round / diamond / cylinder
	Shape string `json:"shape,omitempty"`
	// Group 分组名，用于泳道式布局
	Group string `json:"group,omitempty"`
}

// Edge 是节点之间的连线。
type Edge struct {
	From  string `json:"from"`
	To    string `json:"to"`
	Label string `json:"label,omitempty"`
	// Dashed 虚线，表示异步或弱依赖
	Dashed bool `json:"dashed,omitempty"`
}

// Renderer 生成图解产物。
//
// 输出 SVG：矢量、体积小、任何浏览器可直接显示，
// 且不需要外部渲染引擎（本机没有 mmdc / graphviz / chromium）。
type Renderer struct {
	store *artifacts.Service
}

// NewRenderer 构造渲染器。
func NewRenderer(store *artifacts.Service) *Renderer {
	return &Renderer{store: store}
}

// ErrEmptySpec 规格为空。
var ErrEmptySpec = fmt.Errorf("图解规格为空：需要 mermaid 源码或 nodes/edges")

// Generate 同步生成一张图解，返回已完成的产物。
func (r *Renderer) Generate(ctx context.Context, userID, conversationID string, spec Spec) (*artifacts.Artifact, error) {
	if r == nil || r.store == nil {
		return nil, artifacts.ErrUnavailable
	}

	title := strings.TrimSpace(spec.Title)
	if title == "" {
		title = "图解"
	}

	src, err := build(spec)
	if err != nil {
		return nil, err
	}

	return r.store.CreateSync(ctx, userID, conversationID, artifacts.KindDiagram, title, "diagram.svg",
		func(_ context.Context, req artifacts.ProduceRequest) (artifacts.Produced, error) {
			svg, err := src.render(title)
			if err != nil {
				return artifacts.Produced{}, err
			}
			out := filepath.Join(req.WorkDir, req.OutName)
			if err := os.WriteFile(out, []byte(svg), 0o644); err != nil {
				return artifacts.Produced{}, fmt.Errorf("写入 SVG 失败: %w", err)
			}
			return artifacts.Produced{
				MIME: "image/svg+xml",
				Meta: map[string]any{
					"kind":  src.kind(),
					"nodes": src.nodeCount(),
					"edges": src.edgeCount(),
				},
			}, nil
		}, spec)
}

// build 把 Spec 归一化成可渲染的图。
//
// 两条路径必须产出一致的内部结构，否则「Mermaid 能画、结构化不能画」
// 这类不一致会很难排查。
func build(spec Spec) (*graph, error) {
	if strings.TrimSpace(spec.Mermaid) != "" {
		return parseMermaid(spec.Mermaid)
	}
	if len(spec.Nodes) == 0 {
		return nil, ErrEmptySpec
	}
	return fromStructured(spec.Nodes, spec.Edges), nil
}

// fromStructured 把显式节点与连线转成图。
func fromStructured(nodes []Node, edges []Edge) *graph {
	g := newGraph("flow")
	for _, n := range nodes {
		id := strings.TrimSpace(n.ID)
		if id == "" {
			continue
		}
		label := strings.TrimSpace(n.Label)
		if label == "" {
			label = id
		}
		g.addNode(&node{
			id:    id,
			label: label,
			shape: normalizeShape(n.Shape),
			group: strings.TrimSpace(n.Group),
		})
	}
	for _, e := range edges {
		if strings.TrimSpace(e.From) == "" || strings.TrimSpace(e.To) == "" {
			continue
		}
		g.addEdge(&edge{
			from:   e.From,
			to:     e.To,
			label:  strings.TrimSpace(e.Label),
			dashed: e.Dashed,
		})
	}
	return g
}

func normalizeShape(s string) string {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "round", "rounded", "stadium":
		return shapeRound
	case "diamond", "decision", "rhombus":
		return shapeDiamond
	case "cylinder", "database", "db":
		return shapeCylinder
	default:
		return shapeBox
	}
}
