package diagram

import (
	"fmt"
	"regexp"
	"strings"
)

// 节点形状。
const (
	shapeBox      = "box"
	shapeRound    = "round"
	shapeDiamond  = "diamond"
	shapeCylinder = "cylinder"
)

// node 是图中的一个节点。
type node struct {
	id    string
	label string
	shape string
	group string
	// x / y / w / h 由布局阶段填写
	x, y float64
	w, h float64
}

// edge 是节点之间的连线。
type edge struct {
	from, to string
	label    string
	dashed   bool
}

// graph 是与图类型无关的内部表示。
//
// 布局与绘制只认这个结构，因此 Mermaid 与结构化输入共用同一套渲染，
// 新增图类型时也只需要扩展解析，不需要改绘制。
type graph struct {
	diagramKind string
	nodes       []*node
	edges       []*edge
	byID        map[string]*node
	groups      []string
}

func newGraph(kind string) *graph {
	return &graph{diagramKind: kind, byID: make(map[string]*node)}
}

func (g *graph) addNode(n *node) *node {
	if existing, ok := g.byID[n.id]; ok {
		// 同一节点被多次引用时保留首次定义的标签，避免后者覆盖前者
		//（Mermaid 里 `A[开始]` 之后只写 `A` 很常见）。
		if existing.label == existing.id && n.label != n.id {
			existing.label = n.label
		}
		if n.shape != "" && n.shape != shapeBox {
			existing.shape = n.shape
		}
		if n.group != "" {
			existing.group = n.group
		}
		return existing
	}
	if n.shape == "" {
		n.shape = shapeBox
	}
	g.nodes = append(g.nodes, n)
	g.byID[n.id] = n
	if n.group != "" && !contains(g.groups, n.group) {
		g.groups = append(g.groups, n.group)
	}
	return n
}

func (g *graph) addEdge(e *edge) {
	// 连线两端必须存在，否则渲染时会出现悬空箭头。
	if _, ok := g.byID[e.from]; !ok {
		g.addNode(&node{id: e.from, label: e.from})
	}
	if _, ok := g.byID[e.to]; !ok {
		g.addNode(&node{id: e.to, label: e.to})
	}
	g.edges = append(g.edges, e)
}

func (g *graph) kind() string   { return g.diagramKind }
func (g *graph) nodeCount() int { return len(g.nodes) }
func (g *graph) edgeCount() int { return len(g.edges) }

func contains(list []string, s string) bool {
	for _, v := range list {
		if v == s {
			return true
		}
	}
	return false
}

// ---------- Mermaid 解析 ----------

// nodeDef 匹配节点定义，如 A[标签] / A(标签) / A{标签} / A[(标签)] / A((标签))。
// 三种形状族分别对应方括号、圆括号、花括号，捕获其中的标签文本。
var nodeDef = regexp.MustCompile(
	`([A-Za-z0-9_\-\.]+)\s*(\(\(|\[\(|\[\[|\[|\(|\{)\s*(.*?)\s*(\)\)|\]\)|\]\]|\]|\)|\})`,
)

// edgeLink 匹配一条连线。
//
// 支持 Mermaid 的三种写法：
//
//	A --> B            普通箭头
//	A -->|标签| B       管道标签
//	A -- 标签 --> B     破折号标签
//
// 以及实线/虚线/粗线：--> --- ==> -.-> -.- --x --o
var edgeLink = regexp.MustCompile(
	`([A-Za-z0-9_\-\.]+)` + // 源节点
		`\s*(?:(?:--|-\.)\s*([^\->|]*?)\s*)?` + // 可选「-- 标签」前缀
		`(-->|---|==>|-\.->|-\.-|--x|--o)` + // 箭头
		`\s*(?:\|([^\|]*)\|\s*)?` + // 可选「|标签|」
		`([A-Za-z0-9_\-\.]+)`, // 目标节点
)

// parseMermaid 解析 Mermaid 源码为内部图。
//
// 只覆盖教学场景实际会用到的子集：flowchart / graph / sequenceDiagram /
// stateDiagram。完整实现 Mermaid 语法不是本项目目标，
// 遇到不支持的图类型必须明确报错，而不是画出一张缺元素的图。
func parseMermaid(src string) (*graph, error) {
	lines := strings.Split(src, "\n")

	kind := ""
	var body []string
	for _, raw := range lines {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "%%") {
			continue
		}
		// 去掉 Markdown 代码围栏
		if strings.HasPrefix(line, "```") {
			continue
		}

		if kind == "" {
			lower := strings.ToLower(line)
			switch {
			case strings.HasPrefix(lower, "flowchart"),
				strings.HasPrefix(lower, "graph"),
				strings.HasPrefix(lower, "classdiagram"):
				kind = "flow"
			case strings.HasPrefix(lower, "sequencediagram"):
				kind = "sequence"
			case strings.HasPrefix(lower, "statediagram"):
				kind = "flow"
			case strings.HasPrefix(lower, "erdiagram"):
				kind = "flow"
			default:
				return nil, fmt.Errorf("无法识别的 Mermaid 图类型: %q", line)
			}
			continue
		}

		// 样式与配置语句不影响结构，跳过。
		lower := strings.ToLower(line)
		if strings.HasPrefix(lower, "classdef") ||
			strings.HasPrefix(lower, "class ") ||
			strings.HasPrefix(lower, "style ") ||
			strings.HasPrefix(lower, "linkstyle") ||
			strings.HasPrefix(lower, "subgraph") ||
			strings.HasPrefix(lower, "direction ") ||
			lower == "end" {
			continue
		}

		body = append(body, line)
	}

	if kind == "" {
		return nil, fmt.Errorf("Mermaid 源码缺少图类型声明（如 flowchart TB）")
	}

	if kind == "sequence" {
		return parseSequence(body), nil
	}
	return parseFlow(body), nil
}

// parseFlow 解析 flowchart / state / er 的节点与连线。
//
// 关键点：Mermaid 允许在连线中内联节点定义（A[标签] --> B），
// 因此必须先把定义抽出来替换成裸 id，再解析连线，
// 否则「带标签的节点之间连不上」。
func parseFlow(body []string) *graph {
	g := newGraph("flow")

	for _, line := range body {
		cleaned := extractNodes(g, line)
		parseEdges(g, cleaned)
	}

	return g
}

// extractNodes 抽取一行里的全部节点定义，返回把定义替换成裸 id 后的文本。
func extractNodes(g *graph, line string) string {
	matches := nodeDef.FindAllStringSubmatchIndex(line, -1)
	if len(matches) == 0 {
		return line
	}

	var out strings.Builder
	last := 0
	for _, m := range matches {
		out.WriteString(line[last:m[0]])

		id := line[m[2]:m[3]]
		open := line[m[4]:m[5]]
		label := unquote(line[m[6]:m[7]])

		g.addNode(&node{
			id:    id,
			label: label,
			shape: shapeOf(open),
		})

		out.WriteString(id)
		last = m[1]
	}
	out.WriteString(line[last:])
	return out.String()
}

// parseEdges 解析清洗后的文本中的连线。
//
// 支持链式写法 A --> B --> C：每匹配一条边后，从「目标节点」开始继续，
// 因此链式关系会被拆成多条独立边。
func parseEdges(g *graph, line string) {
	rest := line
	for {
		loc := edgeLink.FindStringSubmatchIndex(rest)
		if loc == nil {
			return
		}

		from := rest[loc[2]:loc[3]]
		arrow := rest[loc[6]:loc[7]]
		to := rest[loc[10]:loc[11]]

		// 标签可能来自「-- 标签」前缀，也可能来自「|标签|」，二者取其一。
		label := ""
		if loc[4] >= 0 && loc[5] > loc[4] {
			label = strings.TrimSpace(rest[loc[4]:loc[5]])
		}
		if label == "" && loc[8] >= 0 && loc[9] > loc[8] {
			label = strings.TrimSpace(rest[loc[8]:loc[9]])
		}

		g.addEdge(&edge{
			from:   from,
			to:     to,
			label:  label,
			dashed: strings.Contains(arrow, "."),
		})

		// 从目标节点继续，让链式写法自然衔接。
		rest = to + rest[loc[1]:]
	}
}

// parseSequence 把时序图转成有向图：参与者为节点，消息为带标签的边。
func parseSequence(body []string) *graph {
	g := newGraph("sequence")

	for _, line := range body {
		lower := strings.ToLower(line)
		if strings.HasPrefix(lower, "participant ") {
			rest := strings.TrimSpace(line[len("participant "):])
			parts := strings.SplitN(rest, " as ", 2)
			id := strings.TrimSpace(parts[0])
			label := id
			if len(parts) == 2 {
				label = strings.TrimSpace(parts[1])
			}
			g.addNode(&node{id: id, label: label, shape: shapeRound})
			continue
		}

		// 消息：A->>B: 文本 / A-->>B: 文本
		for _, arrow := range []string{"-->>", "->>", "-->", "->", "--x", "-x"} {
			idx := strings.Index(line, arrow)
			if idx <= 0 {
				continue
			}
			from := strings.TrimSpace(line[:idx])
			rest := line[idx+len(arrow):]

			to, msg := rest, ""
			if c := strings.Index(rest, ":"); c >= 0 {
				to = strings.TrimSpace(rest[:c])
				msg = strings.TrimSpace(rest[c+1:])
			}
			to = strings.TrimSpace(to)

			// 参与者名不能含空格，含空格说明这不是一条消息。
			if from == "" || to == "" || strings.ContainsAny(from, " ") || strings.ContainsAny(to, " ") {
				continue
			}
			g.addEdge(&edge{
				from:   from,
				to:     to,
				label:  msg,
				dashed: strings.HasPrefix(arrow, "--"),
			})
			break
		}
	}

	return g
}

// shapeOf 按 Mermaid 的括号形式推断节点形状。
func shapeOf(open string) string {
	switch open {
	case "((", "(":
		return shapeRound
	case "{":
		return shapeDiamond
	case "[(", "[[", "[":
		return shapeCylinder2(open)
	default:
		return shapeBox
	}
}

// shapeCylinder2 只有 `[(...)]` 是数据库形状，其余方括号是普通矩形。
func shapeCylinder2(open string) string {
	if open == "[(" {
		return shapeCylinder
	}
	return shapeBox
}

// unquote 清理 Mermaid 标签文本。
//
// 需要处理三种模型常见的写法：
//   - 引号包裹：`A["文本"]` —— 去掉外层引号
//   - 换行标记：`A[第一行<br/>第二行]` —— 转成换行符，由渲染层折行
//   - HTML 实体：`&lt;` `&gt;` `&amp;` —— 还原成字符，避免二次转义后显示为实体
func unquote(s string) string {
	s = strings.TrimSpace(s)

	// 先还原 HTML 实体，模型常把 < > 写成实体形式。
	s = strings.NewReplacer(
		"&lt;", "<",
		"&gt;", ">",
		"&amp;", "&",
		"&quot;", `"`,
		"&#39;", "'",
	).Replace(s)

	// 换行标记统一成换行符。
	s = brTag.ReplaceAllString(s, "\n")

	// 去掉外层引号（可能嵌套一层）
	for i := 0; i < 2 && len(s) >= 2; i++ {
		if (s[0] == '"' && s[len(s)-1] == '"') || (s[0] == '\'' && s[len(s)-1] == '\'') {
			s = strings.TrimSpace(s[1 : len(s)-1])
			continue
		}
		break
	}

	return s
}

// brTag 匹配 Mermaid 标签中的换行标记。
var brTag = regexp.MustCompile(`(?i)<br\s*/?>`)
