package chat

import (
	"context"
	"errors"
	"time"

	"gorm.io/gorm"

	"mentorly/internal/dialogue"
)

// ErrRecordNotFound 资源不存在，屏蔽 gorm 细节。
var ErrRecordNotFound = errors.New("record not found")

// Repo 会话与消息仓储。对外只暴露领域类型。
type Repo struct {
	db *gorm.DB
}

// NewRepo 构造仓储。
func NewRepo(db *gorm.DB) *Repo {
	return &Repo{db: db}
}

// CreateSession 创建会话。
func (r *Repo) CreateSession(ctx context.Context, s *dialogue.Session) error {
	row := &sessionRow{
		ID:     s.ID,
		UserID: s.UserID,
		Title:  s.Title,
	}
	if err := r.db.WithContext(ctx).Create(row).Error; err != nil {
		return err
	}
	// 回填空库默认值，避免调用方拿到零值时间。
	s.LastActiveAt = row.LastActiveAt
	s.CreatedAt = row.CreatedAt
	return nil
}

// GetSession 按 id 查询会话，不含软删除记录。
func (r *Repo) GetSession(ctx context.Context, id string) (*dialogue.Session, error) {
	var row sessionRow
	if err := r.db.WithContext(ctx).First(&row, "id = ?", id).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrRecordNotFound
		}
		return nil, err
	}
	return row.toDomain(), nil
}

// GetSessionForUser 查询会话并校验归属。
// 归属不符时返回 ErrRecordNotFound 而非 403，避免泄露「会话存在但不属于你」。
func (r *Repo) GetSessionForUser(ctx context.Context, id, userID string) (*dialogue.Session, error) {
	var row sessionRow
	if err := r.db.WithContext(ctx).First(&row, "id = ? AND user_id = ?", id, userID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrRecordNotFound
		}
		return nil, err
	}
	return row.toDomain(), nil
}

// ListSessions 列出用户的会话，按最近活跃倒序。
func (r *Repo) ListSessions(ctx context.Context, userID string, limit int) ([]dialogue.Session, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	var rows []sessionRow
	if err := r.db.WithContext(ctx).Where("user_id = ?", userID).
		Order("last_active_at DESC").
		Limit(limit).
		Find(&rows).Error; err != nil {
		return nil, err
	}

	out := make([]dialogue.Session, 0, len(rows))
	for i := range rows {
		out = append(out, *rows[i].toDomain())
	}
	return out, nil
}

// RenameSession 重命名会话（带归属校验）。
func (r *Repo) RenameSession(ctx context.Context, id, userID, title string) error {
	res := r.db.WithContext(ctx).Model(&sessionRow{}).
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
func (r *Repo) DeleteSession(ctx context.Context, id, userID string) error {
	res := r.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).Delete(&sessionRow{})
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return ErrRecordNotFound
	}
	return nil
}

// TouchSession 更新最近活跃时间。
func (r *Repo) TouchSession(ctx context.Context, id string, at time.Time) error {
	return r.db.WithContext(ctx).Model(&sessionRow{}).
		Where("id = ?", id).
		Update("last_active_at", at).Error
}

// CreateMessage 插入消息并回填自增 ID。
//
// sessionID 单独传入而非放进 dialogue.Message：消息本身是纯对话内容，
// 不该为了落库而携带归属字段。tokens 与 meta 由编排层决定（估算或真实用量）。
func (r *Repo) CreateMessage(ctx context.Context, sessionID string, m *dialogue.Message, tokens int, meta MessageMeta) error {
	row := &messageRow{
		SessionID: sessionID,
		Role:      m.Role,
		Content:   m.Content,
		Status:    m.Status,
		Tokens:    tokens,
		Meta:      meta,
	}
	if err := r.db.WithContext(ctx).Create(row).Error; err != nil {
		return err
	}
	m.ID = row.ID
	return nil
}

// ListMessagesBefore 游标分页：取 id < beforeID 的最近 limit 条，按 id 升序返回。
// beforeID 为 0 表示从最新开始。
func (r *Repo) ListMessagesBefore(ctx context.Context, sessionID string, beforeID uint64, limit int) ([]dialogue.Message, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}

	q := r.db.WithContext(ctx).Where("session_id = ?", sessionID)
	if beforeID > 0 {
		q = q.Where("id < ?", beforeID)
	}

	var rows []messageRow
	// 先按 id 倒序取最近 N 条，再反转成升序返回，便于前端直接展示。
	if err := q.Order("id DESC").Limit(limit).Find(&rows).Error; err != nil {
		return nil, err
	}
	reverseRows(rows)

	out := make([]dialogue.Message, 0, len(rows))
	for i := range rows {
		out = append(out, rows[i].toDomain())
	}
	return out, nil
}

// ListMessagesAfter 取 id > afterID 的消息（游标之后），按 id 升序。
func (r *Repo) ListMessagesAfter(ctx context.Context, sessionID string, afterID uint64) ([]dialogue.Message, error) {
	var rows []messageRow
	if err := r.db.WithContext(ctx).Where("session_id = ? AND id > ?", sessionID, afterID).
		Order("id ASC").
		Find(&rows).Error; err != nil {
		return nil, err
	}

	out := make([]dialogue.Message, 0, len(rows))
	for i := range rows {
		out = append(out, rows[i].toDomain())
	}
	return out, nil
}

// ListMessageViews 游标分页查询历史，返回含 tokens / meta 的完整视图。
// 供前端展示用量与耗时，内部编排不使用它（那里只需要对话内容）。
func (r *Repo) ListMessageViews(ctx context.Context, sessionID string, beforeID uint64, limit int) ([]MessageView, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}

	q := r.db.WithContext(ctx).Where("session_id = ?", sessionID)
	if beforeID > 0 {
		q = q.Where("id < ?", beforeID)
	}

	var rows []messageRow
	if err := q.Order("id DESC").Limit(limit).Find(&rows).Error; err != nil {
		return nil, err
	}
	reverseRows(rows)

	out := make([]MessageView, 0, len(rows))
	for i := range rows {
		out = append(out, MessageView{
			Message:   rows[i].toDomain(),
			Tokens:    rows[i].Tokens,
			Meta:      rows[i].Meta,
			CreatedAt: rows[i].CreatedAt,
		})
	}
	return out, nil
}

// CountMessages 统计会话消息条数，用于判断是否首轮。
func (r *Repo) CountMessages(ctx context.Context, sessionID string) (int64, error) {
	var n int64
	err := r.db.WithContext(ctx).Model(&messageRow{}).Where("session_id = ?", sessionID).Count(&n).Error
	return n, err
}

// UpdateSummary 条件更新摘要与游标。
// 用 summary_cursor < cutoff 做条件，防止并发回退（多请求并发时只有前进方向生效）。
func (r *Repo) UpdateSummary(ctx context.Context, sessionID, summary string, cursor uint64, contextTokens int) (bool, error) {
	res := r.db.WithContext(ctx).Model(&sessionRow{}).
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
func (r *Repo) AdvanceMemoryCursor(ctx context.Context, sessionID string, cursor uint64) (bool, error) {
	res := r.db.WithContext(ctx).Model(&sessionRow{}).
		Where("id = ? AND memory_cursor < ?", sessionID, cursor).
		Update("memory_cursor", cursor)
	if res.Error != nil {
		return false, res.Error
	}
	return res.RowsAffected > 0, nil
}

// UpdateContextTokens 记录最近一轮真实上下文用量。
func (r *Repo) UpdateContextTokens(ctx context.Context, sessionID string, tokens int) error {
	return r.db.WithContext(ctx).Model(&sessionRow{}).
		Where("id = ?", sessionID).
		Update("context_tokens", tokens).Error
}

// UpdateTitle 更新会话标题。
func (r *Repo) UpdateTitle(ctx context.Context, sessionID, title string) error {
	return r.db.WithContext(ctx).Model(&sessionRow{}).
		Where("id = ?", sessionID).
		Update("title", title).Error
}

// reverseRows 原地反转切片。
func reverseRows(rows []messageRow) {
	for i, j := 0, len(rows)-1; i < j; i, j = i+1, j-1 {
		rows[i], rows[j] = rows[j], rows[i]
	}
}
