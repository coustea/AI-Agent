package dao

import (
	"context"
	"errors"
	"time"

	"gorm.io/gorm"

	"mentorly/internal/model"
)

// ChatRepo 会话与消息仓储。
type ChatRepo struct {
	db *gorm.DB
}

func NewChatRepo(db *gorm.DB) *ChatRepo {
	return &ChatRepo{db: db}
}

// CreateSession 创建会话。
func (r *ChatRepo) CreateSession(ctx context.Context, s *model.ChatSession) error {
	return r.db.WithContext(ctx).Create(s).Error
}

// GetSession 按 id 查询会话，不含软删除记录。
func (r *ChatRepo) GetSession(ctx context.Context, id string) (*model.ChatSession, error) {
	var s model.ChatSession
	if err := r.db.WithContext(ctx).First(&s, "id = ?", id).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrRecordNotFound
		}
		return nil, err
	}
	return &s, nil
}

// GetSessionForUser 查询会话并校验归属。
// 归属不符时返回 ErrRecordNotFound 而非 403，避免泄露「会话存在但不属于你」。
func (r *ChatRepo) GetSessionForUser(ctx context.Context, id, userID string) (*model.ChatSession, error) {
	var s model.ChatSession
	if err := r.db.WithContext(ctx).First(&s, "id = ? AND user_id = ?", id, userID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrRecordNotFound
		}
		return nil, err
	}
	return &s, nil
}

// ListSessions 列出用户的会话，按最近活跃倒序。
func (r *ChatRepo) ListSessions(ctx context.Context, userID string, limit int) ([]model.ChatSession, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	var list []model.ChatSession
	err := r.db.WithContext(ctx).Where("user_id = ?", userID).
		Order("last_active_at DESC").
		Limit(limit).
		Find(&list).Error
	return list, err
}

// RenameSession 重命名会话（带归属校验）。
func (r *ChatRepo) RenameSession(ctx context.Context, id, userID, title string) error {
	res := r.db.WithContext(ctx).Model(&model.ChatSession{}).
		Where("id = ? AND user_id = ?", id, userID).
		Update("title", title)
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return ErrRecordNotFound
	}
	return nil
}

// DeleteSession 软删除会话。gorm.DeletedAt 会自动带上 deleted_at IS NULL。
func (r *ChatRepo) DeleteSession(ctx context.Context, id, userID string) error {
	res := r.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).Delete(&model.ChatSession{})
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return ErrRecordNotFound
	}
	return nil
}

// TouchSession 更新最近活跃时间。
func (r *ChatRepo) TouchSession(ctx context.Context, id string, at time.Time) error {
	return r.db.WithContext(ctx).Model(&model.ChatSession{}).
		Where("id = ?", id).
		Update("last_active_at", at).Error
}

// CreateMessage 插入消息并回填自增 ID。
func (r *ChatRepo) CreateMessage(ctx context.Context, m *model.ChatMessage) error {
	return r.db.WithContext(ctx).Create(m).Error
}

// UpdateMessage 更新消息内容与状态，用于 assistant 消息落库或回填用量。
func (r *ChatRepo) UpdateMessage(ctx context.Context, m *model.ChatMessage) error {
	return r.db.WithContext(ctx).Model(&model.ChatMessage{}).
		Where("id = ?", m.ID).
		Updates(map[string]any{
			"content": m.Content,
			"status":  m.Status,
			"tokens":  m.Tokens,
			"meta":    m.Meta,
		}).Error
}

// ListMessagesBefore 游标分页：取 id < beforeID 的最近 limit 条，按 id 升序返回。
// beforeID 为 0 表示从最新开始。
func (r *ChatRepo) ListMessagesBefore(ctx context.Context, sessionID string, beforeID uint64, limit int) ([]model.ChatMessage, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}

	q := r.db.WithContext(ctx).Where("session_id = ?", sessionID)
	if beforeID > 0 {
		q = q.Where("id < ?", beforeID)
	}

	var msgs []model.ChatMessage
	// 先按 id 倒序取最近 N 条，再反转成升序返回，便于前端直接展示。
	if err := q.Order("id DESC").Limit(limit).Find(&msgs).Error; err != nil {
		return nil, err
	}
	reverseMessages(msgs)
	return msgs, nil
}

// ListMessagesAfter 取 id > afterID 的消息（游标之后），按 id 升序。
func (r *ChatRepo) ListMessagesAfter(ctx context.Context, sessionID string, afterID uint64) ([]model.ChatMessage, error) {
	var msgs []model.ChatMessage
	err := r.db.WithContext(ctx).Where("session_id = ? AND id > ?", sessionID, afterID).
		Order("id ASC").
		Find(&msgs).Error
	return msgs, err
}

// CountMessages 统计会话消息条数，用于判断是否首轮。
func (r *ChatRepo) CountMessages(ctx context.Context, sessionID string) (int64, error) {
	var n int64
	err := r.db.WithContext(ctx).Model(&model.ChatMessage{}).Where("session_id = ?", sessionID).Count(&n).Error
	return n, err
}

// UpdateSummary 条件更新摘要与游标。
// 用 summary_cursor < cutoff 做条件，防止并发回退（多请求并发时只有前进方向生效）。
func (r *ChatRepo) UpdateSummary(ctx context.Context, sessionID, summary string, cursor uint64, contextTokens int) (bool, error) {
	res := r.db.WithContext(ctx).Model(&model.ChatSession{}).
		Where("id = ? AND summary_cursor < ?", sessionID, cursor).
		Updates(map[string]any{
			"summary":        summary,
			"summary_cursor": cursor,
			"context_tokens": contextTokens,
		})
	if res.Error != nil {
		return false, res.Error
	}
	return res.RowsAffected > 0, nil
}

// AdvanceMemoryCursor 条件推进记忆游标。
func (r *ChatRepo) AdvanceMemoryCursor(ctx context.Context, sessionID string, cursor uint64) (bool, error) {
	res := r.db.WithContext(ctx).Model(&model.ChatSession{}).
		Where("id = ? AND memory_cursor < ?", sessionID, cursor).
		Update("memory_cursor", cursor)
	if res.Error != nil {
		return false, res.Error
	}
	return res.RowsAffected > 0, nil
}

// UpdateContextTokens 记录最近一轮真实上下文用量。
func (r *ChatRepo) UpdateContextTokens(ctx context.Context, sessionID string, tokens int) error {
	return r.db.WithContext(ctx).Model(&model.ChatSession{}).
		Where("id = ?", sessionID).
		Update("context_tokens", tokens).Error
}

// UpdateTitle 更新会话标题。
func (r *ChatRepo) UpdateTitle(ctx context.Context, sessionID, title string) error {
	return r.db.WithContext(ctx).Model(&model.ChatSession{}).
		Where("id = ?", sessionID).
		Update("title", title).Error
}

// reverseMessages 原地反转切片。
func reverseMessages(msgs []model.ChatMessage) {
	for i, j := 0, len(msgs)-1; i < j; i, j = i+1, j-1 {
		msgs[i], msgs[j] = msgs[j], msgs[i]
	}
}
