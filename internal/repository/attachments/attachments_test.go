package attachments

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// TestKindOf 校验扩展名归类。
func TestKindOf(t *testing.T) {
	cases := map[string]string{
		".png":  KindUnknown,
		".jpg":  KindUnknown,
		".pdf":  KindPDF,
		".docx": KindDocx,
		".pptx": KindUnknown,
		".md":   KindText,
		".go":   KindUnknown,
		".exe":  KindUnknown,
		"":      KindUnknown,
	}
	for ext, want := range cases {
		if got := kindOf(ext); got != want {
			t.Errorf("kindOf(%q) = %q, 期望 %q", ext, got, want)
		}
	}
}

// TestSupported 校验支持列表与归类一致。
func TestSupported(t *testing.T) {
	for _, ext := range SupportedExts() {
		if !Supported(ext) {
			t.Errorf("%q 在支持列表中但 Supported 返回 false", ext)
		}
	}
	if Supported(".exe") {
		t.Error(".exe 不应被支持")
	}
}

// TestSanitizeFilename 校验文件名清洗，防止路径注入。
func TestSanitizeFilename(t *testing.T) {
	cases := map[string]string{
		"../../etc/passwd":  "passwd",
		"/absolute/path.md": "path.md",
		"normal.docx":       "normal.docx",
		"":                  "attachment",
		"..":                "attachment",
	}
	for in, want := range cases {
		if got := sanitizeFilename(in); got != want {
			t.Errorf("sanitizeFilename(%q) = %q, 期望 %q", in, got, want)
		}
	}
}

// TestExtractText 校验纯文本提取。
func TestExtractText(t *testing.T) {
	data := []byte("hello\nworld")
	got, err := extract(t.Context(), ".md", data)
	if err != nil {
		t.Fatalf("提取失败: %v", err)
	}
	if got != "hello\nworld" {
		t.Errorf("提取结果 = %q", got)
	}
}

// TestExtractDocx 用真实 docx 验证正文抽取。
//
// 这个测试守着一个实际修过的 bug：结构体标签写成 "w:p" 会匹配不到元素，
// 表现为「解析成功但文本为空」。
func TestExtractDocx(t *testing.T) {
	path := "/tmp/attach_test.docx"
	if _, err := os.Stat(path); err != nil {
		t.Skip("缺少测试文件")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}

	text, err := extractDocx(t.Context(), data)
	if err != nil {
		t.Fatalf("提取失败: %v", err)
	}
	if text == "" {
		t.Fatal("提取为空——检查 xml 标签是否带了 w: 前缀")
	}
	t.Logf("提取 %d 字符", len([]rune(text)))
}

// TestExtractPDF 用真实 PDF 结构验证文本层抽取。
func TestExtractPDF(t *testing.T) {
	if _, err := exec.LookPath("pdftotext"); err != nil {
		t.Skip("缺少 pdftotext")
	}
	content := "BT /F1 12 Tf 72 720 Td (pdf-marker-123) Tj ET"
	objects := []string{
		"<< /Type /Catalog /Pages 2 0 R >>",
		"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
		"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
		fmt.Sprintf("<< /Length %d >>\nstream\n%s\nendstream", len(content), content),
	}
	var pdf bytes.Buffer
	pdf.WriteString("%PDF-1.4\n")
	offsets := make([]int, len(objects)+1)
	for i, obj := range objects {
		offsets[i+1] = pdf.Len()
		fmt.Fprintf(&pdf, "%d 0 obj\n%s\nendobj\n", i+1, obj)
	}
	xref := pdf.Len()
	fmt.Fprintf(&pdf, "xref\n0 %d\n0000000000 65535 f \n", len(offsets))
	for _, offset := range offsets[1:] {
		fmt.Fprintf(&pdf, "%010d 00000 n \n", offset)
	}
	fmt.Fprintf(&pdf, "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n", len(offsets), xref)
	text, err := extract(t.Context(), ".pdf", pdf.Bytes())
	if err != nil {
		t.Fatalf("提取失败: %v", err)
	}
	if !bytes.Contains([]byte(text), []byte("pdf-marker-123")) {
		t.Fatalf("PDF 文本提取不完整: %q", text)
	}
}

// TestExtractDocxInvalid 非法输入必须报错，不能静默返回空。
func TestExtractDocxInvalid(t *testing.T) {
	if _, err := extractDocx(t.Context(), []byte("not a zip")); err == nil {
		t.Error("非法 docx 应报错")
	}
}

// TestAttachmentRelDir 附件目录必须按「用户/会话」分层。
//
// 附件与 Agent 工作区同根，会话隔离靠这两段目录名实现。
func TestAttachmentRelDir(t *testing.T) {
	got, err := attachmentRelDir("u1", "c1")
	if err != nil {
		t.Fatal(err)
	}
	if want := filepath.Join("u1", "c1"); got != want {
		t.Errorf("relDir = %q, 期望 %q", got, want)
	}
}

// TestAttachmentRelDirRejectsEscape 目录名来自上下文，仍须拒绝路径逃逸。
func TestAttachmentRelDirRejectsEscape(t *testing.T) {
	cases := []struct{ user, conv string }{
		{"../etc", "c1"},
		{"u1", "../c1"},
		{"u1/../..", "c1"},
		{"u1", "c1/../../x"},
		{"", "c1"},
		{"u1", ""},
	}
	for _, c := range cases {
		if _, err := attachmentRelDir(c.user, c.conv); err == nil {
			t.Errorf("attachmentRelDir(%q, %q) 应报错", c.user, c.conv)
		}
	}
}

// TestSaveRejectsEmptyConversation 附件必须归属某个会话，否则无法与工作区对齐。
func TestSaveRejectsEmptyConversation(t *testing.T) {
	dir := t.TempDir()
	st := &Store{cfg: Config{Dir: dir, MaxBytes: 1 << 20, MaxExtractChars: 100}}

	_, err := st.Save(context.Background(), "u1", "", "a.txt", bytes.NewReader([]byte("hi")))
	if !errors.Is(err, ErrInvalidUpload) {
		t.Fatalf("空会话 ID 应返回 ErrInvalidUpload, 实际 %v", err)
	}
}

// TestSavePathLandsInsideWorkspace 附件必须落在会话工作区内。
//
// 这是本次修复的核心：此前 Save 只按 userID 建目录，附件与工作区不同根，
// Agent 的 /workspace 挂载看不到文件，Skill 脚本拿不到真实路径。
func TestSavePathLandsInsideWorkspace(t *testing.T) {
	root := t.TempDir() // 模拟 workspace/chat，附件根与工作区同根
	userID, convID := "u1", "c1"

	relDir, err := attachmentRelDir(userID, convID)
	if err != nil {
		t.Fatal(err)
	}

	// 模拟 Save 的落盘位置
	full := filepath.Join(root, relDir, "att_1.pdf")
	if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(full, []byte("PDF"), 0o644); err != nil {
		t.Fatal(err)
	}

	// 工作区视角：{root}/{uid}/{cid}
	workspace, err := filepath.Abs(filepath.Join(root, userID, convID))
	if err != nil {
		t.Fatal(err)
	}
	abs, err := filepath.Abs(full)
	if err != nil {
		t.Fatal(err)
	}
	rel, err := filepath.Rel(workspace, abs)
	if err != nil {
		t.Fatal(err)
	}
	if rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		t.Fatalf("附件落在工作区之外: 工作区=%q 附件=%q", workspace, abs)
	}
	if want := "att_1.pdf"; rel != want {
		t.Errorf("相对工作区路径 = %q, 期望 %q", rel, want)
	}
}

func TestOriginalStatusAndMissingRead(t *testing.T) {
	dir := t.TempDir()
	s := &Store{cfg: Config{Dir: dir}}
	a := &Attachment{ID: "a", Stored: "a.txt", Ext: ".md", Text: "缓存预览"}
	if got := s.Status(a); got != "original_missing" {
		t.Fatal(got)
	}
	if err := os.WriteFile(filepath.Join(dir, "a.txt"), []byte("完整原件"), 0600); err != nil {
		t.Fatal(err)
	}
	if got := s.Status(a); got != "available" {
		t.Fatal(got)
	}
	a.ExtractError = "提取失败"
	if got := s.Status(a); got != "extraction_failed" {
		t.Fatal(got)
	}
	if a.ID != "a" || a.Text != "缓存预览" {
		t.Fatal("状态检查不能删除附件信息")
	}
}

func TestSaveRejectsOversizedText(t *testing.T) {
	dir := t.TempDir()
	st := &Store{cfg: Config{Dir: dir, MaxBytes: 1 << 20, MaxExtractChars: 10}}

	_, err := st.Save(t.Context(), "u1", "c1", "long.md", bytes.NewReader([]byte(strings.Repeat("字", 11))))
	if !errors.Is(err, ErrInvalidUpload) {
		t.Fatalf("超字数文档应返回 ErrInvalidUpload, 实际: %v", err)
	}
	entries, err := os.ReadDir(filepath.Join(dir, "u1", "c1"))
	if err == nil && len(entries) > 0 {
		t.Fatalf("拒传后应清理临时文件，实际残留: %d", len(entries))
	}
}
