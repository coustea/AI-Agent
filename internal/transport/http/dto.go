package http

import (
	"time"

	"mentorly/internal/agents/tutor"
)

// CreateConversationReq 创建会话请求。标题可留空，由首轮回答异步生成。
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
	// AttachmentIDs 本次消息携带的附件 ID 列表。
	// 只接受服务端生成的 ID，不接受前端传入的文件路径。
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
	ID            uint64    `json:"id"`
	Role          string    `json:"role"`
	Content       string    `json:"content"`
	Status        string    `json:"status"`
	Tokens        int       `json:"tokens,omitempty"`
	AttachmentIDs []string  `json:"attachment_ids,omitempty"`
	CreatedAt     time.Time `json:"created_at"`
}

func toConversationResp(c *tutor.Conversation) ConversationResp {
	return ConversationResp{
		ID:        c.ID,
		Title:     c.Title,
		CreatedAt: c.CreatedAt,
		UpdatedAt: c.UpdatedAt,
	}
}

func toConversationList(rows []tutor.Conversation) []ConversationResp {
	out := make([]ConversationResp, 0, len(rows))
	for i := range rows {
		out = append(out, toConversationResp(&rows[i]))
	}
	return out
}

func toMessageList(rows []tutor.Message) []MessageResp {
	out := make([]MessageResp, 0, len(rows))
	for i := range rows {
		m := &rows[i]
		out = append(out, MessageResp{
			ID:            m.ID,
			Role:          m.Role,
			Content:       m.Content,
			Status:        m.Status,
			Tokens:        m.Tokens,
			AttachmentIDs: m.AttachmentIDs,
			CreatedAt:     m.CreatedAt,
		})
	}
	return out
}
