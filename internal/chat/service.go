package chat

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"

	"mentorly/internal/dialogue"
)

// ErrSessionNotFound 会话不存在或无权访问。
var ErrSessionNotFound = errors.New("会话不存在")

// Service 是会话的管理面：创建、列表、重命名、删除、历史分页。
//
// 它与 turn.Orchestrator 的分工：
//   - Service 管理「会话这行数据」的增删改查，不参与生成；
//   - Orchestrator 管理「一轮对话」的生命周期，不决定会话如何创建。
//
// 旧实现把两者混在一个 ChatService 里，导致一半方法只是转发 dao，
// 而真正的核心操作 RunTurn 又必须被 handler 绕过它直接调用。
type Service struct {
	repo *Repo
}

// NewService 构造会话管理服务。
func NewService(repo *Repo) *Service {
	return &Service{repo: repo}
}

// Create 创建会话。标题留空时用默认标题，首轮回答后异步生成真实标题。
func (s *Service) Create(ctx context.Context, userID, title string) (*dialogue.Session, error) {
	title = strings.TrimSpace(title)
	if title == "" {
		title = "新会话"
	}

	sess := &dialogue.Session{
		ID:     uuid.NewString(),
		UserID: userID,
		Title:  title,
	}
	if err := s.repo.CreateSession(ctx, sess); err != nil {
		return nil, fmt.Errorf("创建会话失败: %w", err)
	}
	return sess, nil
}

// List 列出用户的会话。
func (s *Service) List(ctx context.Context, userID string, limit int) ([]dialogue.Session, error) {
	rows, err := s.repo.ListSessions(ctx, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("查询会话列表失败: %w", err)
	}
	return rows, nil
}

// Rename 重命名会话。
func (s *Service) Rename(ctx context.Context, userID, sessionID, title string) error {
	err := s.repo.RenameSession(ctx, sessionID, userID, strings.TrimSpace(title))
	if err != nil {
		if errors.Is(err, ErrRecordNotFound) {
			return ErrSessionNotFound
		}
		return fmt.Errorf("重命名会话失败: %w", err)
	}
	return nil
}

// Delete 软删除会话。
func (s *Service) Delete(ctx context.Context, userID, sessionID string) error {
	if err := s.repo.DeleteSession(ctx, sessionID, userID); err != nil {
		if errors.Is(err, ErrRecordNotFound) {
			return ErrSessionNotFound
		}
		return fmt.Errorf("删除会话失败: %w", err)
	}
	return nil
}

// Messages 游标分页查询历史（含 tokens 与 meta 的完整视图）。
func (s *Service) Messages(ctx context.Context, userID, sessionID string, beforeID uint64, limit int) ([]MessageView, error) {
	// 先校验归属，避免越权读取他人消息。
	if _, err := s.repo.GetSessionForUser(ctx, sessionID, userID); err != nil {
		if errors.Is(err, ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	rows, err := s.repo.ListMessageViews(ctx, sessionID, beforeID, limit)
	if err != nil {
		return nil, fmt.Errorf("查询消息失败: %w", err)
	}
	return rows, nil
}
