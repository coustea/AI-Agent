package dto

import "time"

// CreateConversationReq 创建会话请求。标题可留空，取首个问题的前 20 个字符。
type CreateConversationReq struct {
	Title string `json:"title" binding:"max=200"`
}

// RenameConversationReq 重命名会话请求。
type RenameConversationReq struct {
	Title string `json:"title" binding:"required,min=1,max=200"`
}

// SendMessageReq 发送消息请求。
type SendMessageReq struct {
	Content string `json:"content" binding:"required,max=20000"`
	// AttachmentIDs 只接受服务端生成的附件 ID，不接受文件路径。
	AttachmentIDs []string `json:"attachment_ids,omitempty" binding:"max=10"`
}

// ConversationResp 会话响应。
type ConversationResp struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// MessageResp 消息响应。
type MessageResp struct {
	ID            uint64   `json:"id"`
	Role          string   `json:"role"`
	Content       string   `json:"content"`
	Status        string   `json:"status"`
	Tokens        int      `json:"tokens,omitempty"`
	AttachmentIDs []string `json:"attachment_ids,omitempty"`
	// Attachments 按上传顺序排列的附件摘要。
	//
	// 与 AttachmentIDs 并存而非取代：ID 顺序是消息与附件关联的事实来源，
	// Attachments 是可直接渲染的展开结果。前端一次请求就能把消息与附件
	// 按顺序画出来，不必再为每条消息发一轮请求。
	Attachments []AttachmentBrief `json:"attachments,omitempty"`
	CreatedAt   time.Time         `json:"created_at"`
}

// AttachmentBrief 是嵌入消息响应的附件摘要。
//
// 只放渲染缩略信息：正文、提取文本等大字段不在列表接口里返回，
// 需要时走 /api/v1/attachments/:id。
type AttachmentBrief struct {
	ID       string `json:"id"`
	Filename string `json:"filename"`
	Kind     string `json:"kind"`
	MIME     string `json:"mime"`
	Size     int64  `json:"size"`
	// DownloadURL 直接可下载的原件地址
	DownloadURL string `json:"download_url"`
}
