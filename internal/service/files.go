package service

import (
	"context"
	"fmt"
	"io"
	"os"
	"sort"
	"syscall"
	"time"

	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
	"mentorly/internal/utils"
)

type Attachment = attachments.Attachment

var (
	ErrAttachmentNotFound = attachments.ErrNotFound
	ErrInvalidUpload      = attachments.ErrInvalidUpload
	ErrUnsafePath         = utils.ErrUnsafePath
)

// Attachments 负责校验会话归属后的附件读写。
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

// WorkspaceFile 描述会话工作区顶层常规文件。
type WorkspaceFile struct {
	Name       string
	Size       int64
	ModifiedAt time.Time
}

// Workspace 在确认会话归属后安全列出或打开会话工作区产物。
type Workspace struct {
	root          string
	conversations *conversations.Store
}

func NewWorkspace(root string, conversations *conversations.Store) *Workspace {
	return &Workspace{root: root, conversations: conversations}
}

func (s *Workspace) List(ctx context.Context, userID, conversationID string) ([]WorkspaceFile, error) {
	if _, err := s.conversations.GetConversation(ctx, conversationID, userID); err != nil {
		return nil, err
	}
	return listWorkspaceDir(s.root, userID, conversationID)
}

func (s *Workspace) Open(ctx context.Context, userID, conversationID, name string) (*os.File, os.FileInfo, error) {
	if _, err := s.conversations.GetConversation(ctx, conversationID, userID); err != nil {
		return nil, nil, err
	}
	return openWorkspaceFile(s.root, userID, conversationID, name)
}

func listWorkspaceDir(root, userID, conversationID string) ([]WorkspaceFile, error) {
	dir, err := utils.SafeJoin(root, userID, conversationID)
	if err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(dir)
	if os.IsNotExist(err) {
		return []WorkspaceFile{}, nil
	}
	if err != nil {
		return nil, fmt.Errorf("读取工作区失败: %w", err)
	}
	out := make([]WorkspaceFile, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || entry.Type()&os.ModeSymlink != 0 {
			continue
		}
		info, err := entry.Info()
		if err != nil || !info.Mode().IsRegular() {
			continue
		}
		out = append(out, WorkspaceFile{Name: entry.Name(), Size: info.Size(), ModifiedAt: info.ModTime()})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ModifiedAt.After(out[j].ModifiedAt) })
	return out, nil
}

func openWorkspaceFile(root, userID, conversationID, name string) (*os.File, os.FileInfo, error) {
	dir, err := utils.SafeJoin(root, userID, conversationID)
	if err != nil {
		return nil, nil, err
	}
	path, err := utils.SafeJoin(dir, name)
	if err != nil {
		return nil, nil, err
	}
	f, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, nil, err
	}
	info, err := f.Stat()
	if err != nil || !info.Mode().IsRegular() {
		f.Close()
		return nil, nil, fmt.Errorf("文件不存在")
	}
	return f, info, nil
}
