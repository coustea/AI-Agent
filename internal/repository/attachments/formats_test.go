package attachments

import (
	"archive/zip"
	"bytes"
	"errors"
	"os/exec"
	"strings"
	"testing"
)

func TestUploadFormatAllowlist(t *testing.T) {
	s := &Store{}
	for _, ext := range []string{".png", ".jpg", ".pptx", ".txt", ".csv", ".html", ".exe", ""} {
		if Supported(ext) {
			t.Fatalf("不应支持 %q", ext)
		}
		if _, err := s.Save(t.Context(), "u", "c", "file"+ext, strings.NewReader("data")); !errors.Is(err, ErrInvalidUpload) {
			t.Fatalf("%s 未在落盘前拒绝: %v", ext, err)
		}
	}
	for _, ext := range []string{".doc", ".docx", ".pdf", ".md", ".DOCX"} {
		if !Supported(ext) {
			t.Fatalf("应支持 %s", ext)
		}
	}
}

func TestDocTextExtraction(t *testing.T) {
	if _, err := exec.LookPath("textutil"); err != nil {
		t.Skip("需要 macOS textutil")
	}
	cmd := exec.CommandContext(t.Context(), "textutil", "-convert", "doc", "-format", "txt", "-stdin", "-stdout", "-inputencoding", "UTF-8")
	cmd.Stdin = strings.NewReader("DOC中文内容 document-marker")
	data, err := cmd.Output()
	if err != nil {
		t.Fatal(err)
	}
	text, err := extract(t.Context(), ".doc", data)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(text, "DOC中文内容") || !strings.Contains(text, "document-marker") {
		t.Fatalf("DOC 正文丢失: %q", text)
	}
}

func TestDocxParagraphAndTable(t *testing.T) {
	var b bytes.Buffer
	z := zip.NewWriter(&b)
	f, err := z.Create("word/document.xml")
	if err != nil {
		t.Fatal(err)
	}
	_, err = f.Write([]byte(`<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>段落中文 marker</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>表格单元</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>`))
	if err != nil {
		t.Fatal(err)
	}
	rels, err := z.Create("word/_rels/document.xml.rels")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := rels.Write([]byte(`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>`)); err != nil {
		t.Fatal(err)
	}
	styles, err := z.Create("word/styles.xml")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := styles.Write([]byte(`<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>`)); err != nil {
		t.Fatal(err)
	}
	if err := z.Close(); err != nil {
		t.Fatal(err)
	}
	first, err := extract(t.Context(), ".docx", b.Bytes())
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(first, "段落中文") || !strings.Contains(first, "表格单元") {
		t.Fatalf("正文或表格丢失: %q", first)
	}
	for i := 0; i < 10; i++ {
		again, err := extract(t.Context(), ".docx", b.Bytes())
		if err != nil || again != first {
			t.Fatalf("分页读取要求提取顺序稳定: %v", err)
		}
	}
}

func TestInvalidDocumentContents(t *testing.T) {
	for _, ext := range []string{".doc", ".docx", ".pdf"} {
		if _, err := extract(t.Context(), ext, []byte("not a document")); err == nil {
			t.Fatalf("%s 应报告解析失败", ext)
		}
	}
	if _, err := extract(t.Context(), ".md", []byte{0xff, 0}); err == nil {
		t.Fatal("应拒绝二进制 Markdown")
	}
}

func TestDocxParserPanicBecomesExtractionError(t *testing.T) {
	var b bytes.Buffer
	z := zip.NewWriter(&b)
	for name, content := range map[string]string{
		"word/document.xml":            `<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>`,
		"word/_rels/document.xml.rels": `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>`,
	} {
		f, err := z.Create(name)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := f.Write([]byte(content)); err != nil {
			t.Fatal(err)
		}
	}
	if err := z.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := extract(t.Context(), ".docx", b.Bytes()); err == nil {
		t.Fatal("缺少样式的文档应报告提取失败，不能崩溃")
	}
}
