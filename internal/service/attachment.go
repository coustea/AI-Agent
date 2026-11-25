package service

import (
	"context"
	"io"
	"os"

	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
)

type Attachment = attachments.Attachment

var ErrAttachmentNotFound = attachments.ErrNotFound
var ErrInvalidUpload = attachments.ErrInvalidUpload

// Attachments 在文件操作前校验会话归属。
type Attachments struct {
	store         *attachments.Store
	conversations *conversations.Store
}

func NewAttachments(store *attachments.Store, conversations *conversations.Store) *Attachments {
	return &Attachments{store: store, conversations: conversations}
}

func (s *Attachments) MaxBytes() int64 { return s.store.Config().MaxBytes }

func (s *Attachments) Save(ctx context.Context, userID, conversationID, filename string, body io.Reader) (*attachments.Attachment, error) {
	if _, err := s.conversations.GetConversation(ctx, conversationID, userID); err != nil {
		return nil, err
	}
	return s.store.Save(ctx, userID, conversationID, filename, body)
}

func (s *Attachments) Get(ctx context.Context, userID, id string) (*attachments.Attachment, error) {
	return s.store.GetForUser(ctx, id, userID)
}

func (s *Attachments) Open(a *attachments.Attachment) (*os.File, error) {
	return s.store.Open(a)
}
