package service

import (
	"context"
	"os"

	"mentorly/internal/repository/conversations"
	"mentorly/internal/repository/files"
	"mentorly/internal/utils"
)

var ErrUnsafePath = utils.ErrUnsafePath

// Workspace 在访问文件前确认会话属于当前用户。
type Workspace struct {
	conversations *conversations.Store
	files         *files.Workspace
}

func NewWorkspace(root string, conversations *conversations.Store) *Workspace {
	return &Workspace{conversations: conversations, files: files.NewWorkspace(root)}
}

func (s *Workspace) List(ctx context.Context, userID, conversationID string) ([]files.File, error) {
	if _, err := s.conversations.GetConversation(ctx, conversationID, userID); err != nil {
		return nil, err
	}
	return s.files.List(userID, conversationID)
}

func (s *Workspace) Open(ctx context.Context, userID, conversationID, name string) (*os.File, os.FileInfo, error) {
	if _, err := s.conversations.GetConversation(ctx, conversationID, userID); err != nil {
		return nil, nil, err
	}
	return s.files.Open(userID, conversationID, name)
}
