// Package dto 存放跨层传输对象：请求体与响应体。
package dto

import "time"

// CreateSessionReq 创建会话请求。标题可留空，由首轮回答异步生成。
type CreateSessionReq struct {
	Title string `json:"title" binding:"max=100"`
}

// RenameSessionReq 重命名会话请求。
type RenameSessionReq struct {
	Title string `json:"title" binding:"required,min=1,max=100"`
}

// SessionResp 会话摘要响应。
type SessionResp struct {
	ID           string    `json:"id"`
	Title        string    `json:"title"`
	LastActiveAt time.Time `json:"last_active_at"`
	CreatedAt    time.Time `json:"created_at"`
}

// SendMessageReq 发送消息请求。
type SendMessageReq struct {
	Content string `json:"content" binding:"required,max=20000"`
}

// MessageResp 消息响应。
type MessageResp struct {
	ID        uint64          `json:"id"`
	Role      string          `json:"role"`
	Content   string          `json:"content"`
	Status    string          `json:"status"`
	Tokens    int             `json:"tokens"`
	Meta      *MessageMetaDTO `json:"meta,omitempty"`
	CreatedAt time.Time       `json:"created_at"`
}

// MessageMetaDTO 消息元信息。
type MessageMetaDTO struct {
	PromptTokens     int   `json:"prompt_tokens,omitempty"`
	CompletionTokens int   `json:"completion_tokens,omitempty"`
	TotalTokens      int   `json:"total_tokens,omitempty"`
	ElapsedMS        int64 `json:"elapsed_ms,omitempty"`
}

// MemoryResp 长期记忆响应。
type MemoryResp struct {
	Content   string    `json:"content"`
	Version   int       `json:"version"`
	UpdatedAt time.Time `json:"updated_at"`
}

// UpdateMemoryReq 手动编辑记忆请求。
type UpdateMemoryReq struct {
	Content string `json:"content"`
}
