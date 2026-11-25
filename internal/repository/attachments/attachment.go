package attachments

import (
	"strings"
	"time"
)

// 附件类别。
const (
	KindDoc     = "doc"
	KindPDF     = "pdf"
	KindDocx    = "docx"
	KindText    = "text"
	KindUnknown = "unknown"
)

// Attachment 是一次上传的附件元数据。
type Attachment struct {
	ID             string
	UserID         string
	ConversationID string
	// Filename 用户上传时的原始文件名，仅用于展示
	Filename string
	// Ext 小写扩展名，含点
	Ext  string
	Kind string
	MIME string
	Size int64
	// Stored 相对存储根的文件名，由服务端生成，不含用户输入
	Stored string
	// Text 提取出的文本（预览）
	Text string
	// ExtractError 提取失败原因。非空表示该附件无法被模型读取，
	// 必须如实告知用户，而不是当作空附件处理。
	ExtractError string
	// Truncated 文本是否被截断
	Truncated bool
	CreatedAt time.Time
}

// kindOf 按扩展名归类。
func kindOf(ext string) string {
	switch strings.ToLower(ext) {
	case ".doc":
		return KindDoc
	case ".docx":
		return KindDocx
	case ".pdf":
		return KindPDF
	case ".md":
		return KindText
	default:
		return KindUnknown
	}
}

func mimeOf(ext string) string {
	switch strings.ToLower(ext) {
	case ".doc":
		return "application/msword"
	case ".docx":
		return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
	case ".pdf":
		return "application/pdf"
	case ".md":
		return "text/markdown; charset=utf-8"
	default:
		return "application/octet-stream"
	}
}

func Supported(ext string) bool { return kindOf(ext) != KindUnknown }
func SupportedExts() []string   { return []string{".doc", ".docx", ".pdf", ".md"} }
