package attachments

import (
	"archive/zip"
	"bytes"
	"encoding/xml"
	"fmt"
	"io"
	"regexp"
	"strings"
)

// 解析 PDF / DOCX / PPTX 的纯 Go 实现。
//
// 为什么不用第三方库：
//   - DOCX/PPTX 本质是 ZIP + XML，抽取正文只需要读几个固定部件；
//   - PDF 的文本层可以用内容流中的 Tj/TJ 操作符抽取，
//     对教学场景常见的电子版 PDF 足够；
//   - 引入 pdfcpu / unioffice 这类库会显著增加依赖体积与授权风险。
//
// 明确的能力边界（不可回避）：
//   - 扫描版 PDF（纯图片）没有文本层，抽取结果为空，会如实报错；
//   - 复杂排版（多栏、表格）抽取后顺序可能不完美；
//   - PDF 中文字体若使用自定义编码且无 ToUnicode 表，文字无法还原。

// ---------- DOCX ----------

// docxDocument 是 word/document.xml 的最小结构。
//
// 注意：Go 的 encoding/xml 在匹配时只比较 local name（忽略 w: 前缀），
// 但结构体标签必须写不带前缀的名字，写成 "w:p" 会匹配不到任何元素——
// 这正是「解析成功但文本为空」的原因。
type docxDocument struct {
	Body struct {
		Paragraphs []docxParagraph `xml:"p"`
	} `xml:"body"`
}

// docxParagraph 是一个段落。
type docxParagraph struct {
	// Runs 是段落内的文本片段
	Runs []docxRun `xml:"r"`
	// Hyperlinks 里的文本也属于正文
	Hyperlinks []docxParagraph `xml:"hyperlink"`
	// Tables 里的单元格段落
	Tables []docxTable `xml:"tbl"`
}

// docxRun 是一个文本片段。
type docxRun struct {
	// Text 是可见文本
	Text string `xml:"t"`
	// Tab / Break 表示制表符与换行，忽略即可
	Tab   *struct{} `xml:"tab"`
	Break *struct{} `xml:"br"`
}

// docxTable 是表格，仅用于抽取其中的段落文本。
type docxTable struct {
	Rows []docxRow `xml:"tr"`
}

type docxRow struct {
	Cells []docxParagraph `xml:"tc"`
}

// text 返回段落自身的可见文本。
func (p docxParagraph) text() string {
	var sb strings.Builder
	for _, r := range p.Runs {
		sb.WriteString(r.Text)
		if r.Break != nil {
			sb.WriteString("\n")
		}
		if r.Tab != nil {
			sb.WriteString("\t")
		}
	}
	return sb.String()
}

// allText 递归收集段落（含超链接与表格）中的文本。
func (p docxParagraph) allText() []string {
	var out []string
	if t := strings.TrimSpace(p.text()); t != "" {
		out = append(out, t)
	}
	for _, h := range p.Hyperlinks {
		out = append(out, h.allText()...)
	}
	for _, tbl := range p.Tables {
		for _, row := range tbl.Rows {
			var cells []string
			for _, cell := range row.Cells {
				if t := strings.TrimSpace(cell.text()); t != "" {
					cells = append(cells, t)
				}
				for _, h := range cell.Hyperlinks {
					cells = append(cells, h.allText()...)
				}
			}
			if len(cells) > 0 {
				out = append(out, strings.Join(cells, " | "))
			}
		}
	}
	return out
}

// extractDocx 抽取 docx 正文。
func extractDocx(data []byte) (string, error) {
	zr, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return "", fmt.Errorf("docx 不是有效的 ZIP 包: %w", err)
	}

	var target *zip.File
	for _, f := range zr.File {
		if f.Name == "word/document.xml" {
			target = f
			break
		}
	}
	if target == nil {
		return "", fmt.Errorf("docx 缺少 word/document.xml")
	}

	rc, err := target.Open()
	if err != nil {
		return "", fmt.Errorf("读取 docx 正文失败: %w", err)
	}
	defer rc.Close()

	raw, err := io.ReadAll(io.LimitReader(rc, 64<<20))
	if err != nil {
		return "", fmt.Errorf("读取 docx 正文失败: %w", err)
	}

	var doc docxDocument
	if err := xml.Unmarshal(raw, &doc); err != nil {
		return "", fmt.Errorf("解析 docx XML 失败: %w", err)
	}

	var lines []string
	for _, p := range doc.Body.Paragraphs {
		lines = append(lines, p.allText()...)
	}
	return strings.TrimSpace(strings.Join(lines, "\n")), nil
}

// ---------- PPTX ----------

// extractPPTX 按幻灯片顺序抽取文本。
func extractPPTX(data []byte) (string, error) {
	zr, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return "", fmt.Errorf("pptx 不是有效的 ZIP 包: %w", err)
	}

	// 幻灯片文件名形如 ppt/slides/slide1.xml，需要按页码数字排序。
	type slideFile struct {
		name string
		num  int
	}
	var slides []slideFile

	for _, f := range zr.File {
		name := f.Name
		if !strings.HasPrefix(name, "ppt/slides/slide") || !strings.HasSuffix(name, ".xml") {
			continue
		}
		num := 0
		if _, err := fmt.Sscanf(name, "ppt/slides/slide%d.xml", &num); err != nil {
			continue
		}
		slides = append(slides, slideFile{name: name, num: num})
	}
	if len(slides) == 0 {
		return "", fmt.Errorf("pptx 中没有找到幻灯片")
	}

	// 按页码升序
	for i := 0; i < len(slides); i++ {
		for j := i + 1; j < len(slides); j++ {
			if slides[j].num < slides[i].num {
				slides[i], slides[j] = slides[j], slides[i]
			}
		}
	}

	var sb strings.Builder
	for _, s := range slides {
		text, err := readPPTXSlide(zr, s.name)
		if err != nil {
			continue
		}
		if strings.TrimSpace(text) == "" {
			continue
		}
		sb.WriteString(fmt.Sprintf("【第 %d 页】\n", s.num))
		sb.WriteString(text)
		sb.WriteString("\n\n")
	}
	return strings.TrimSpace(sb.String()), nil
}

// readPPTXSlide 抽取单页中的全部 a:t 文本。
func readPPTXSlide(zr *zip.Reader, name string) (string, error) {
	var target *zip.File
	for _, f := range zr.File {
		if f.Name == name {
			target = f
			break
		}
	}
	if target == nil {
		return "", fmt.Errorf("找不到 %s", name)
	}

	rc, err := target.Open()
	if err != nil {
		return "", err
	}
	defer rc.Close()

	raw, err := io.ReadAll(io.LimitReader(rc, 16<<20))
	if err != nil {
		return "", err
	}

	// 幻灯片里的文本散落在 a:t 中，逐个提取即可保持大致阅读顺序。
	var out []string
	dec := xml.NewDecoder(bytes.NewReader(raw))
	for {
		tok, err := dec.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return "", err
		}
		if se, ok := tok.(xml.StartElement); ok && se.Name.Local == "t" {
			var s string
			if err := dec.DecodeElement(&s, &se); err == nil {
				if t := strings.TrimSpace(s); t != "" {
					out = append(out, t)
				}
			}
		}
	}
	return strings.Join(out, "\n"), nil
}

// ---------- PDF ----------

// pdfTextOp 匹配 PDF 内容流里的字符串操作数：
//   - (文本) Tj
//   - [(文本) -100 (文本)] TJ
var pdfTextBlock = regexp.MustCompile(`(?s)\[(.*?)\]\s*TJ|\((.*?)\)\s*Tj`)

// pdfString 匹配括号内的字面量字符串，处理转义。
var pdfLiteral = regexp.MustCompile(`\((?:\\.|[^\\()])*\)`)

// extractPDF 抽取 PDF 文本层。
//
// 做法：解压 FlateDecode 流，从内容流中提取 Tj/TJ 的字符串操作数。
// 这是「够用」的实现，不处理字体编码映射，因此对使用
// 标准 WinAnsi/MacRoman 编码的文档效果最好。
func extractPDF(data []byte) (string, error) {
	streams, err := pdfStreams(data)
	if err != nil {
		return "", err
	}

	var sb strings.Builder
	for _, s := range streams {
		text := pdfTextOf(s)
		if text != "" {
			sb.WriteString(text)
			sb.WriteString("\n")
		}
	}

	out := strings.TrimSpace(sb.String())
	if out == "" {
		return "", fmt.Errorf("PDF 未包含可提取的文本层（可能是扫描件或纯图片 PDF）")
	}
	return out, nil
}

// pdfStreams 提取所有可解压的内容流。
func pdfStreams(data []byte) ([]string, error) {
	var out []string

	// 逐个查找 stream ... endstream 块。
	rest := data
	for {
		start := bytes.Index(rest, []byte("stream"))
		if start < 0 {
			break
		}
		// 跳过 "stream" 后的换行（\r\n 或 \n）
		body := rest[start+len("stream"):]
		body = bytes.TrimPrefix(body, []byte("\r\n"))
		body = bytes.TrimPrefix(body, []byte("\n"))

		end := bytes.Index(body, []byte("endstream"))
		if end < 0 {
			break
		}

		chunk := body[:end]
		rest = body[end+len("endstream"):]

		// 流可能是 FlateDecode 压缩的，也可能直接是明文。
		if decoded, err := inflate(chunk); err == nil {
			out = append(out, decoded)
			continue
		}
		out = append(out, string(chunk))
	}

	if len(out) == 0 {
		return nil, fmt.Errorf("PDF 中未找到内容流")
	}
	return out, nil
}

// pdfTextOf 从一个内容流中抽取文字。
func pdfTextOf(stream string) string {
	// 只处理看起来像内容流的块：必须包含文本操作符。
	if !strings.Contains(stream, "Tj") && !strings.Contains(stream, "TJ") {
		return ""
	}

	var lines []string
	for _, m := range pdfTextBlock.FindAllStringSubmatch(stream, -1) {
		var parts []string
		if m[1] != "" {
			// TJ 数组：提取其中每个字符串
			for _, lit := range pdfLiteral.FindAllString(m[1], -1) {
				parts = append(parts, decodePDFString(lit))
			}
		} else {
			parts = append(parts, decodePDFString(m[2]))
		}
		line := strings.Join(parts, "")
		if strings.TrimSpace(line) != "" {
			lines = append(lines, line)
		}
	}
	return strings.Join(lines, " ")
}

// decodePDFString 去掉括号并处理常见转义。
func decodePDFString(s string) string {
	s = strings.TrimPrefix(s, "(")
	s = strings.TrimSuffix(s, ")")

	var sb strings.Builder
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c != '\\' {
			sb.WriteByte(c)
			continue
		}
		i++
		if i >= len(s) {
			break
		}
		switch s[i] {
		case 'n':
			sb.WriteByte('\n')
		case 'r':
			sb.WriteByte('\r')
		case 't':
			sb.WriteByte('\t')
		case '(', ')', '\\':
			sb.WriteByte(s[i])
		default:
			sb.WriteByte(s[i])
		}
	}
	return sb.String()
}
