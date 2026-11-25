package attachments

import (
	"archive/zip"
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	docx "github.com/cloudwego/eino-ext/components/document/parser/docx"
)

// extract 只分派已支持的格式，正文解析交给官方扩展或系统转换器。
func extract(ctx context.Context, ext string, data []byte) (string, error) {
	ctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()
	if err := ctx.Err(); err != nil {
		return "", err
	}
	switch strings.ToLower(ext) {
	case ".md":
		if !utf8.Valid(data) || bytes.IndexByte(data, 0) >= 0 {
			return "", fmt.Errorf("Markdown 必须是 UTF-8 文本")
		}
		return string(data), nil
	case ".docx":
		return extractDocx(ctx, data)
	case ".doc":
		// 旧版 Word 必须是 OLE 二进制，不能把其他格式改名后交给转换器。
		if !bytes.HasPrefix(data, []byte{0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1}) {
			return "", fmt.Errorf("不是有效的 Word DOC 二进制文件")
		}
		return extractCommand(ctx, data, "textutil", "-convert", "txt", "-format", "doc", "-stdin", "-stdout", "-encoding", "UTF-8", "-noload", "-nostore")
	case ".pdf":
		if !bytes.HasPrefix(bytes.TrimSpace(data), []byte("%PDF-")) {
			return "", fmt.Errorf("不是有效的 PDF 文件")
		}
		return extractCommand(ctx, data, "pdftotext", "-layout", "-enc", "UTF-8", "-", "-")
	default:
		return "", fmt.Errorf("仅支持 doc、docx、pdf、md 附件")
	}
}

func extractDocx(ctx context.Context, data []byte) (text string, err error) {
	// 当前官方扩展的底层解析器对缺失 styles.xml 等输入会 panic。
	// 在第三方边界转换成提取失败，保留原件和附件引用。
	defer func() {
		if recover() != nil {
			text, err = "", fmt.Errorf("DOCX 文本提取失败：解析器无法处理此文档结构")
		}
	}()
	// 官方解析器负责 XML；在调用前限制 ZIP 解压体积。
	z, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return "", fmt.Errorf("DOCX 文件无效: %w", err)
	}
	var total uint64
	const maxExpanded = 64 << 20
	for _, f := range z.File {
		if f.UncompressedSize64 > maxExpanded-total {
			return "", fmt.Errorf("DOCX 解压后超过 64 MB")
		}
		total += f.UncompressedSize64
	}
	p, err := docx.NewDocxParser(ctx, &docx.Config{ToSections: true, IncludeTables: true})
	if err != nil {
		return "", err
	}
	docs, err := p.Parse(ctx, bytes.NewReader(data))
	if err != nil {
		return "", fmt.Errorf("DOCX 文本提取失败: %w", err)
	}
	if err := ctx.Err(); err != nil {
		return "", err
	}
	// 官方解析器按 map 遍历章节，排序后保证按字符分页的 offset 稳定。
	sort.SliceStable(docs, func(i, j int) bool {
		a, _ := docx.GetSectionType(docs[i])
		b, _ := docx.GetSectionType(docs[j])
		return a < b
	})
	var parts []string
	for _, d := range docs {
		if d != nil {
			parts = append(parts, d.Content)
		}
	}
	return strings.TrimSpace(strings.Join(parts, "\n")), nil
}

func extractCommand(ctx context.Context, data []byte, name string, args ...string) (string, error) {
	bin, err := exec.LookPath(name)
	if err != nil {
		return "", fmt.Errorf("文档解析需要 %s: %w", name, err)
	}
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Stdin = bytes.NewReader(data)
	out, err := cmd.Output()
	if ctx.Err() != nil {
		return "", ctx.Err()
	}
	if err != nil {
		return "", fmt.Errorf("%s 文本提取失败: %w", name, err)
	}
	text := strings.TrimSpace(string(out))
	if text == "" {
		return "", fmt.Errorf("文件没有可提取的文本（扫描件需要 OCR，目前不支持）")
	}
	return text, nil
}
