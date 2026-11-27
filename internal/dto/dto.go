package dto

import "time"

type RegisterReq struct {
	Username string `json:"username" binding:"required,min=2,max=50"`
	Password string `json:"password" binding:"required,min=6,max=80"`
	Email    string `json:"email" binding:"required,email,max=100"`
}

type LoginReq struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

type UserResp struct {
	ID       string `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email"`
}

type LoginResp struct {
	Token string   `json:"token"`
	User  UserResp `json:"user"`
}

type CreateConversationReq struct {
	Title string `json:"title" binding:"max=200"`
}

type RenameConversationReq struct {
	Title string `json:"title" binding:"required,min=1,max=200"`
}

type SendMessageReq struct {
	Content       string   `json:"content" binding:"required,max=20000"`
	AttachmentIDs []string `json:"attachment_ids,omitempty" binding:"max=10"`
}

type ConversationResp struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type MessageResp struct {
	ID            uint64            `json:"id"`
	Role          string            `json:"role"`
	Content       string            `json:"content"`
	Status        string            `json:"status"`
	Tokens        int               `json:"tokens,omitempty"`
	AttachmentIDs []string          `json:"attachment_ids,omitempty"`
	Attachments   []AttachmentBrief `json:"attachments,omitempty"`
	CreatedAt     time.Time         `json:"created_at"`
}

type AttachmentBrief struct {
	ID          string `json:"id"`
	Filename    string `json:"filename"`
	Kind        string `json:"kind"`
	MIME        string `json:"mime"`
	Size        int64  `json:"size"`
	DownloadURL string `json:"download_url"`
}

type AttachmentResp struct {
	ID           string `json:"id"`
	Filename     string `json:"filename"`
	Kind         string `json:"kind"`
	MIME         string `json:"mime"`
	Size         int64  `json:"size"`
	TextLength   int    `json:"text_length,omitempty"`
	ExtractError string `json:"extract_error,omitempty"`
	DownloadURL  string `json:"download_url"`
}

type FileResp struct {
	Name        string `json:"name"`
	Path        string `json:"path"`
	Size        int64  `json:"size"`
	ModifiedAt  string `json:"modified_at"`
	DownloadURL string `json:"download_url"`
}
