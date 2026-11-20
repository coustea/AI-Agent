package diagram

import (
	"strings"
	"testing"
)

// TestParseMermaidFlow 覆盖流程图的核心语法。
//
// 这些用例对应真实踩过的坑：带标签的连线一度完全解析不出来，
// 因为节点定义与连线语法在正则里互相干扰。
func TestParseMermaidFlow(t *testing.T) {
	cases := []struct {
		name      string
		src       string
		wantNodes int
		wantEdges int
	}{
		{
			name: "基本连线与条件标签",
			src: `flowchart TB
    A[用户请求] --> B{是否命中缓存}
    B -- 是 --> C[返回缓存]
    B -- 否 --> D[查询数据库]
    D --> E[(MySQL)]
    C --> F[响应]
    D --> F`,
			wantNodes: 6,
			wantEdges: 6,
		},
		{
			name: "链式写法",
			src: `flowchart LR
    A[开始] --> B[处理] --> C[结束]`,
			wantNodes: 3,
			wantEdges: 2,
		},
		{
			name: "管道标签与虚线",
			src: `graph TD
    A -->|成功| B
    A -.->|失败| C`,
			wantNodes: 3,
			wantEdges: 2,
		},
		{
			name: "裸节点引用",
			src: `flowchart TB
    A[入口] --> B
    B --> C[出口]`,
			wantNodes: 3,
			wantEdges: 2,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			g, err := parseMermaid(tc.src)
			if err != nil {
				t.Fatalf("解析失败: %v", err)
			}
			if g.nodeCount() != tc.wantNodes {
				t.Errorf("节点数 = %d, 期望 %d", g.nodeCount(), tc.wantNodes)
			}
			if g.edgeCount() != tc.wantEdges {
				t.Errorf("连线数 = %d, 期望 %d", g.edgeCount(), tc.wantEdges)
			}
		})
	}
}

// TestParseMermaidSequence 覆盖时序图。
func TestParseMermaidSequence(t *testing.T) {
	src := `sequenceDiagram
    participant U as 用户
    participant S as 服务端
    U->>S: 提交问题
    S-->>U: 流式回答`

	g, err := parseMermaid(src)
	if err != nil {
		t.Fatalf("解析失败: %v", err)
	}
	if g.nodeCount() != 2 {
		t.Errorf("参与者数 = %d, 期望 2", g.nodeCount())
	}
	if g.edgeCount() != 2 {
		t.Errorf("消息数 = %d, 期望 2", g.edgeCount())
	}
	if g.kind() != "sequence" {
		t.Errorf("kind = %q", g.kind())
	}
}

// TestParseMermaidErrors 未声明图类型必须报错，而不是画出空图。
func TestParseMermaidErrors(t *testing.T) {
	for _, src := range []string{
		"",
		"A[节点] --> B[节点]",
		"unknownDiagram\n  A --> B",
	} {
		if _, err := parseMermaid(src); err == nil {
			t.Errorf("期望报错，实际成功: %q", src)
		}
	}
}

// TestLabelCleanup 校验标签清洗：引号、br 换行、HTML 实体。
//
// 模型经常输出 A["文本<br/>第二行"] 这类写法，
// 若不清洗，SVG 里会显示字面量 <br/> 与多余引号。
func TestLabelCleanup(t *testing.T) {
	src := `flowchart LR
    A["带引号的标签"] --> B["第一行<br/>第二行"]
    B --> C["a &amp; b"]`

	g, err := parseMermaid(src)
	if err != nil {
		t.Fatalf("解析失败: %v", err)
	}

	for _, n := range g.nodes {
		if strings.HasPrefix(n.label, `"`) || strings.HasSuffix(n.label, `"`) {
			t.Errorf("标签残留引号: %q", n.label)
		}
		if strings.Contains(strings.ToLower(n.label), "<br") {
			t.Errorf("标签残留 br 标记: %q", n.label)
		}
		if strings.Contains(n.label, "&amp;") {
			t.Errorf("标签残留 HTML 实体: %q", n.label)
		}
	}

	if got := g.byID["A"].label; got != "带引号的标签" {
		t.Errorf("A 标签 = %q", got)
	}
	if got := g.byID["B"].label; got != "第一行\n第二行" {
		t.Errorf("B 标签 = %q", got)
	}
	if got := g.byID["C"].label; got != "a & b" {
		t.Errorf("C 标签 = %q", got)
	}
}

// TestRenderSVG 校验渲染产物是合法 SVG 且含关键元素。
func TestRenderSVG(t *testing.T) {
	src := `flowchart TB
    A[开始] --> B{判断}
    B -- 是 --> C[结束]`

	g, err := parseMermaid(src)
	if err != nil {
		t.Fatalf("解析失败: %v", err)
	}

	out, err := g.render("测试标题")
	if err != nil {
		t.Fatalf("渲染失败: %v", err)
	}

	for _, want := range []string{
		"<svg", "</svg>", "测试标题", "开始", "判断", "结束",
		"marker-end", // 箭头
	} {
		if !strings.Contains(out, want) {
			t.Errorf("SVG 缺少 %q", want)
		}
	}

	// 不能出现二次转义
	if strings.Contains(out, "&amp;amp;") || strings.Contains(out, "&amp;lt;") {
		t.Error("SVG 存在二次转义")
	}

	// 必须有合理的画布尺寸
	if strings.Contains(out, `width="0"`) || strings.Contains(out, `height="0"`) {
		t.Error("SVG 尺寸为 0")
	}
}

// TestRenderEmptyGraph 空图必须报错而不是产出空文件。
func TestRenderEmptyGraph(t *testing.T) {
	g := newGraph("flow")
	if _, err := g.render("空"); err == nil {
		t.Error("空图应返回错误")
	}
}

// TestFromStructured 校验结构化输入的渲染路径。
func TestFromStructured(t *testing.T) {
	g := fromStructured([]Node{
		{ID: "a", Label: "入口"},
		{ID: "b", Label: "出口", Shape: "diamond"},
	}, []Edge{
		{From: "a", To: "b", Label: "条件"},
	})

	if g.nodeCount() != 2 || g.edgeCount() != 1 {
		t.Fatalf("nodes=%d edges=%d", g.nodeCount(), g.edgeCount())
	}
	if g.byID["b"].shape != shapeDiamond {
		t.Errorf("形状 = %q, 期望 diamond", g.byID["b"].shape)
	}
}

// TestWrapLabel 校验中文折行不会切断字符。
func TestWrapLabel(t *testing.T) {
	lines := wrapLabel("这是一个很长的中文标签需要折行显示", 6)
	if len(lines) == 0 {
		t.Fatal("折行结果为空")
	}
	var joined strings.Builder
	for _, l := range lines {
		joined.WriteString(l)
	}
	// 折行只是插入断点，不能丢字符（末行可能被省略号替换）
	if !strings.HasPrefix("这是一个很长的中文标签需要折行显示", strings.TrimSuffix(lines[0], "…")) {
		t.Errorf("首行不是原文前缀: %q", lines[0])
	}
}

// TestDisplayWidth CJK 宽度应为 ASCII 的两倍。
func TestDisplayWidth(t *testing.T) {
	if got := displayWidth("ab"); got != 2 {
		t.Errorf("ASCII 宽度 = %v, 期望 2", got)
	}
	if got := displayWidth("中文"); got != 4 {
		t.Errorf("CJK 宽度 = %v, 期望 4", got)
	}
}
