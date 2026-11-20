package presentation

import (
	"archive/zip"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestBuildPPTXStructure 校验产出的 pptx 是一个结构完整的 OOXML 包。
//
// 这里不做「打开文件看一眼」这种弱验证，而是逐项检查：
//   - ZIP 可读且无损坏；
//   - 必需的部件齐全（少一个 PowerPoint 就会提示修复）；
//   - 每页幻灯片都有自己的 rels；
//   - 中文文本确实写进了 slide XML。
func TestBuildPPTXStructure(t *testing.T) {
	dir := t.TempDir()
	out := filepath.Join(dir, "deck.pptx")

	slides := []slideContent{
		{Title: "封面标题", Bullets: []string{"副标题文本"}},
		{Title: "第一页", Bullets: []string{"要点一", "要点二"}},
		{Title: "第二页", Bullets: []string{"中文内容测试"}},
	}

	if err := buildPPTX(out, slides, "测试课件"); err != nil {
		t.Fatalf("生成失败: %v", err)
	}

	st, err := os.Stat(out)
	if err != nil {
		t.Fatalf("文件不存在: %v", err)
	}
	if st.Size() == 0 {
		t.Fatal("生成的文件为空")
	}

	zr, err := zip.OpenReader(out)
	if err != nil {
		t.Fatalf("不是有效 ZIP: %v", err)
	}
	defer zr.Close()

	// 必需部件：缺任何一个都会导致 PowerPoint 报错。
	required := []string{
		"[Content_Types].xml",
		"_rels/.rels",
		"ppt/presentation.xml",
		"ppt/_rels/presentation.xml.rels",
		"ppt/slideMasters/slideMaster1.xml",
		"ppt/slideMasters/_rels/slideMaster1.xml.rels",
		"ppt/slideLayouts/slideLayout1.xml",
		"ppt/slideLayouts/_rels/slideLayout1.xml.rels",
		"ppt/theme/theme1.xml",
		"docProps/core.xml",
		"docProps/app.xml",
	}

	found := make(map[string]*zip.File)
	for _, f := range zr.File {
		found[f.Name] = f
	}

	for _, name := range required {
		if _, ok := found[name]; !ok {
			t.Errorf("缺少必需部件: %s", name)
		}
	}

	// 每页幻灯片及其 rels
	for i := 1; i <= len(slides); i++ {
		slide := "ppt/slides/slide" + itoa(i) + ".xml"
		rels := "ppt/slides/_rels/slide" + itoa(i) + ".xml.rels"
		if _, ok := found[slide]; !ok {
			t.Errorf("缺少幻灯片: %s", slide)
		}
		if _, ok := found[rels]; !ok {
			t.Errorf("缺少幻灯片关系: %s", rels)
		}
	}

	// 中文必须真的写进去了
	body := readZipFile(t, found["ppt/slides/slide1.xml"])
	if !strings.Contains(body, "封面标题") {
		t.Error("slide1 缺少中文标题")
	}
	if !strings.Contains(body, "副标题文本") {
		t.Error("slide1 缺少中文副标题")
	}
}

// TestPPTXXMLWellFormed 校验关键部件是合法 XML 片段。
func TestPPTXXMLWellFormed(t *testing.T) {
	cases := map[string]string{
		"contentTypes":  contentTypes(2),
		"presentation":  presentationXML(2),
		"slideMaster":   slideMasterXML(),
		"slideLayout":   slideLayoutXML(),
		"theme":         themeXML(),
		"rootRels":      rootRels(),
		"presentationR": presentationRels(2),
	}

	for name, xml := range cases {
		t.Run(name, func(t *testing.T) {
			if !strings.HasPrefix(xml, `<?xml`) {
				t.Error("缺少 XML 声明")
			}
			if !balancedTags(xml) {
				t.Error("标签不配对")
			}
		})
	}
}

// TestSlideXMLContent 校验文本走完整 run 链路。
//
// 裸 <a:t> 没有 <a:r> 包裹时 PowerPoint 不渲染文字，
// 这是 OOXML 里最容易踩的坑之一。
func TestSlideXMLContent(t *testing.T) {
	xml := slideXML(slideContent{
		Title:   "标题",
		Bullets: []string{"第一点", "第二点"},
	})

	for _, want := range []string{"<a:r>", "<a:rPr", "<a:t>标题</a:t>", "<a:t>第一点</a:t>", "<a:t>第二点</a:t>"} {
		if !strings.Contains(xml, want) {
			t.Errorf("缺少 %q", want)
		}
	}

	// 多行文本应拆成多个 a:p，而不是一个带 \n 的段落
	if strings.Contains(xml, "第一点\n第二点") {
		t.Error("文本未按行拆分")
	}
}

// TestEscapeXML 校验特殊字符转义，避免生成非法 XML。
func TestEscapeXML(t *testing.T) {
	got := escapeXML(`a & b < c > d " e ' f`)
	want := `a &amp; b &lt; c &gt; d &quot; e &apos; f`
	if got != want {
		t.Errorf("转义结果 = %q", got)
	}
}

// TestSpecValidate 校验规格校验的边界。
func TestSpecValidate(t *testing.T) {
	valid := Spec{
		Title: "课件",
		Slides: []Slide{
			{Title: "第一页", Bullets: []string{"要点"}},
		},
	}
	if err := valid.Validate(); err != nil {
		t.Errorf("合法规格被拒: %v", err)
	}

	invalid := []struct {
		name string
		spec Spec
	}{
		{"空标题", Spec{Slides: []Slide{{Title: "页", Bullets: []string{"x"}}}}},
		{"无幻灯片", Spec{Title: "课件"}},
		{"页缺标题", Spec{Title: "课件", Slides: []Slide{{Bullets: []string{"x"}}}}},
		{"页无内容", Spec{Title: "课件", Slides: []Slide{{Title: "页"}}}},
		{"要点过多", Spec{Title: "课件", Slides: []Slide{{Title: "页", Bullets: []string{"1", "2", "3", "4", "5", "6", "7"}}}}},
	}

	for _, tc := range invalid {
		t.Run(tc.name, func(t *testing.T) {
			if err := tc.spec.Validate(); err == nil {
				t.Error("期望校验失败")
			}
		})
	}
}

// TestToSlides 校验封面被单独插入。
func TestToSlides(t *testing.T) {
	slides := toSlides(Spec{
		Title:    "课件标题",
		Subtitle: "副标题",
		Slides:   []Slide{{Title: "页一", Bullets: []string{"a"}}},
	})

	if len(slides) != 2 {
		t.Fatalf("页数 = %d, 期望 2（封面 + 1 页）", len(slides))
	}
	if slides[0].Title != "课件标题" {
		t.Errorf("封面标题 = %q", slides[0].Title)
	}
}

// ---------- 测试辅助 ----------

func readZipFile(t *testing.T, f *zip.File) string {
	t.Helper()
	if f == nil {
		t.Fatal("文件不存在")
	}
	rc, err := f.Open()
	if err != nil {
		t.Fatalf("打开失败: %v", err)
	}
	defer rc.Close()

	data, err := io.ReadAll(rc)
	if err != nil {
		t.Fatalf("读取失败: %v", err)
	}
	return string(data)
}

// balancedTags 粗略检查标签配对数量（不追求完整 XML 解析）。
func balancedTags(s string) bool {
	opens := strings.Count(s, "<a:") + strings.Count(s, "<p:")
	closes := strings.Count(s, "</a:") + strings.Count(s, "</p:")
	// 自闭合标签会让 opens 多于 closes，因此只要求 closes <= opens
	return closes <= opens
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	var b []byte
	for n > 0 {
		b = append([]byte{byte('0' + n%10)}, b...)
		n /= 10
	}
	return string(b)
}
