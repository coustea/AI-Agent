// Package attachments 处理用户上传的附件：存储、文本提取与多模态引用。
//
// 设计原则：
//   - 附件一律用 attachment_id 引用，绝不信任前端传入的文件路径；
//   - 每次访问都校验归属，跨用户访问返回与「不存在」相同的错误；
//   - 模型原生支持的格式（图片）走多模态直传；
//   - 文档（PDF/DOCX/PPTX）提取为文本后再进 Prompt，避免塞入二进制；
//   - 无法解析的附件必须明确告知，不允许静默忽略。
package attachments

import (
	"time"
)

// 附件类别。
const (
	KindImage   = "image"
	KindPDF     = "pdf"
	KindDocx    = "docx"
	KindPPTX    = "pptx"
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
	// Text 提取出的文本（文档类），图片为空
	Text string
	// ExtractError 提取失败原因。非空表示该附件无法被模型读取，
	// 必须如实告知用户，而不是当作空附件处理。
	ExtractError string
	// Truncated 文本是否被截断
	Truncated bool
	CreatedAt time.Time
}

// NativeImage 判断是否可作为图片直接送入模型。
// 只支持 OpenAI 兼容协议普遍接受的格式。
func (a *Attachment) NativeImage() bool {
	switch a.Ext {
	case ".png", ".jpg", ".jpeg", ".webp", ".gif":
		return true
	}
	return false
}

// Readable 判断附件是否可供模型读取（原生图片或有可用文本）。
func (a *Attachment) Readable() bool {
	return a.NativeImage() || a.Text != ""
}

// kindOf 按扩展名归类。
func kindOf(ext string) string {
	switch ext {
	case ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp":
		return KindImage
	case ".pdf":
		return KindPDF
	case ".docx":
		return KindDocx
	case ".pptx":
		return KindPPTX
	case ".txt", ".md", ".csv", ".json", ".log", ".go", ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".rs", ".sql", ".yaml", ".yml", ".xml", ".html", ".css":
		return KindText
	default:
		return KindUnknown
	}
}

// mimeOf 按扩展名推断 MIME。
func mimeOf(ext string) string {
	switch ext {
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".webp":
		return "image/webp"
	case ".gif":
		return "image/gif"
	case ".pdf":
		return "application/pdf"
	case ".docx":
		return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
	case ".pptx":
		return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
	case ".txt", ".md", ".csv", ".log":
		return "text/plain; charset=utf-8"
	case ".json":
		return "application/json"
	case ".html":
		return "text/html; charset=utf-8"
	default:
		return "application/octet-stream"
	}
}

// Supported 判断扩展名是否在支持列表内。
func Supported(ext string) bool {
	return kindOf(ext) != KindUnknown
}

// SupportedExts 返回支持的扩展名，用于错误提示。
func SupportedExts() []string {
	return []string{".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".docx", ".pptx", ".txt", ".md", ".csv", ".json", ".go", ".py", ".js", ".ts"}
}
