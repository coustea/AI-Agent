package attachments

import (
	"bytes"
	"os"
	"testing"
)

// TestKindOf 校验扩展名归类。
func TestKindOf(t *testing.T) {
	cases := map[string]string{
		".png":  KindImage,
		".jpg":  KindImage,
		".pdf":  KindPDF,
		".docx": KindDocx,
		".pptx": KindPPTX,
		".md":   KindText,
		".go":   KindText,
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

// TestNativeImage 只有浏览器与模型都支持的图片格式才算原生。
func TestNativeImage(t *testing.T) {
	for _, ext := range []string{".png", ".jpg", ".jpeg", ".webp", ".gif"} {
		a := &Attachment{Ext: ext}
		if !a.NativeImage() {
			t.Errorf("%q 应为原生图片", ext)
		}
	}
	for _, ext := range []string{".bmp", ".pdf", ".docx"} {
		a := &Attachment{Ext: ext}
		if a.NativeImage() {
			t.Errorf("%q 不应为原生图片", ext)
		}
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
	got, err := extract(".txt", data)
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

	text, err := extractDocx(data)
	if err != nil {
		t.Fatalf("提取失败: %v", err)
	}
	if text == "" {
		t.Fatal("提取为空——检查 xml 标签是否带了 w: 前缀")
	}
	t.Logf("提取 %d 字符", len([]rune(text)))
}

// TestExtractPDF 用最小 PDF 验证文本层抽取。
func TestExtractPDF(t *testing.T) {
	path := "/tmp/attach_test.pdf"
	if _, err := os.Stat(path); err != nil {
		t.Skip("缺少测试文件")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}

	text, err := extractPDF(data)
	if err != nil {
		t.Fatalf("提取失败: %v", err)
	}
	if text == "" {
		t.Fatal("提取为空")
	}
	t.Logf("提取 %d 字符: %q", len([]rune(text)), text)
}

// TestExtractDocxInvalid 非法输入必须报错，不能静默返回空。
func TestExtractDocxInvalid(t *testing.T) {
	if _, err := extractDocx([]byte("not a zip")); err == nil {
		t.Error("非法 docx 应报错")
	}
}

// TestInflate 校验 zlib 与裸 deflate 两条解压路径。
func TestInflate(t *testing.T) {
	// 空数据应报错
	if _, err := inflate(nil); err == nil {
		t.Error("空数据应报错")
	}
	// 随机字节应报错
	if _, err := inflate([]byte{0xFF, 0xFF, 0xFF, 0xFF}); err == nil {
		t.Error("无效压缩数据应报错")
	}
}

// TestBuildUserMessageNoAttachments 无附件时退化为纯文本消息。
func TestBuildUserMessageNoAttachments(t *testing.T) {
	msg, err := BuildUserMessage(t.Context(), nil, "u1", "问题", nil)
	if err != nil {
		t.Fatalf("构造失败: %v", err)
	}
	if msg.Content != "问题" {
		t.Errorf("Content = %q", msg.Content)
	}
	if len(msg.UserInputMultiContent) != 0 {
		t.Error("无附件时不应有多模态部件")
	}
}

// TestAttachmentReadable 校验可读性判定。
func TestAttachmentReadable(t *testing.T) {
	img := &Attachment{Ext: ".png"}
	if !img.Readable() {
		t.Error("图片应可读")
	}

	doc := &Attachment{Ext: ".pdf", Text: "内容"}
	if !doc.Readable() {
		t.Error("有文本的文档应可读")
	}

	empty := &Attachment{Ext: ".pdf", ExtractError: "无文本层"}
	if empty.Readable() {
		t.Error("提取失败的文档不应可读")
	}
}

// TestReadBytes 校验读取原始字节。
func TestReadBytes(t *testing.T) {
	dir := t.TempDir()
	st := &Store{cfg: Config{Dir: dir}}

	if err := os.MkdirAll(dir+"/u1", 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(dir+"/u1/a.png", []byte("PNGDATA"), 0o644); err != nil {
		t.Fatal(err)
	}

	a := &Attachment{Stored: "u1/a.png"}
	data, err := ReadBytes(st, a)
	if err != nil {
		t.Fatalf("读取失败: %v", err)
	}
	if !bytes.Equal(data, []byte("PNGDATA")) {
		t.Errorf("内容 = %q", data)
	}
}
