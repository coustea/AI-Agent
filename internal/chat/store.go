package chat

import (
	"context"
	"errors"
	"time"

	"gorm.io/gorm"
)

// ErrRecordNotFound 资源不存在，屏蔽 gorm 细节。
var ErrRecordNotFound = errors.New("record not found")

// sessionRow 对应 chat_sessions 表。
//
// 设计要点：
//   - Summary 直接存在于会话行上，不存成 system 消息。一条会话只有一份摘要，
//     消息表因此只保留真实对话，查询与游标推进都更清晰。
//   - SummaryCursor 是消息自增 id 的水位线，用于「游标之后的消息」这类查询；
//     推进时用条件更新防止并发回退。
//   - ContextTokens 是最近一轮真实上下文 TotalTokens（含 Prompt），
//     用于下一轮判断是否达压缩阈值。
type sessionRow struct {
	ID     string `gorm:"column:id;type:varchar(36);primaryKey"`
	UserID string `gorm:"column:user_id;type:varchar(36);not null;index:idx_chat_sessions_user,priority:1"`
	Title  string `gorm:"column:title;type:varchar(100);not null;default:'新会话'"`

	Summary       string `gorm:"column:summary;type:text;not null"`
	SummaryCursor uint64 `gorm:"column:summary_cursor;type:bigint unsigned;not null;default:0"`
	ContextTokens int    `gorm:"column:context_tokens;type:int;not null;default:0"`

	LastActiveAt time.Time      `gorm:"column:last_active_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);index:idx_chat_sessions_user,priority:3"`
	CreatedAt    time.Time      `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime"`
	UpdatedAt    time.Time      `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime"`
	DeletedAt    gorm.DeletedAt `gorm:"column:deleted_at;type:datetime(3);index:idx_chat_sessions_user,priority:2"`
}

func (sessionRow) TableName() string { return "chat_sessions" }

// toDomain 把存储行转成领域类型。
func (r *sessionRow) toDomain() *Session {
	return &Session{
		ID:            r.ID,
		UserID:        r.UserID,
		Title:         r.Title,
		Summary:       r.Summary,
		SummaryCursor: r.SummaryCursor,
		ContextTokens: r.ContextTokens,
		LastActiveAt:  r.LastActiveAt,
		CreatedAt:     r.CreatedAt,
	}
}

// messageRow 对应 chat_messages 表。
// ID 使用自增 bigint，因为游标依赖单调递增。
type messageRow struct {
	ID        uint64      `gorm:"column:id;type:bigint unsigned;primaryKey;autoIncrement"`
	SessionID string      `gorm:"column:session_id;type:varchar(36);not null;index:idx_chat_messages_session,priority:1"`
	Role      string      `gorm:"column:role;type:varchar(16);not null"`
	Content   string      `gorm:"column:content;type:longtext;not null"`
	Status    string      `gorm:"column:status;type:varchar(16);not null;default:completed"`
	Tokens    int         `gorm:"column:tokens;type:int;not null;default:0"`
	Meta      MessageMeta `gorm:"column:meta;type:json;serializer:json"`
	CreatedAt time.Time   `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_chat_messages_session,priority:2"`
}

func (messageRow) TableName() string { return "chat_messages" }

// toDomain 把存储行转成领域类型。
func (r *messageRow) toDomain() Message {
	return Message{
		ID:      r.ID,
		Role:    r.Role,
		Content: r.Content,
		Status:  r.Status,
	}
}

// toView 转成带元信息的完整视图。
func (r *messageRow) toView() MessageView {
	return MessageView{
		Message:   r.toDomain(),
		Tokens:    r.Tokens,
		Meta:      r.Meta,
		CreatedAt: r.CreatedAt,
	}
}

// Store 是会话与消息的持久化。
//
// 对外只暴露领域类型（Session / Message / MessageView），
// GORM 行类型与表名不出本文件。
type Store struct {
	db *gorm.DB
}

// NewStore 构造仓储。
func NewStore(db *gorm.DB) *Store {
	return &Store{db: db}
}

// Schema 声明本包拥有的表，供启动期 AutoMigrate 使用。
func Schema() []any { return []any{&sessionRow{}, &messageRow{}} }

// ---------- 会话 ----------

// CreateSession 创建会话。
func (s *Store) CreateSession(ctx context.Context, sess *Session) error {
	// 显式填入时间而不是依赖数据库默认值：
	// gorm 对带 default 标签的列走「交给数据库」路径，Create 后结构体里仍是零值，
	// 调用方（HTTP 响应）就会拿到 0001-01-01。这里先赋值再落库，两边一致。
	now := time.Now()
	row := &sessionRow{
		ID:           sess.ID,
		UserID:       sess.UserID,
		Title:        sess.Title,
		LastActiveAt: now,
		CreatedAt:    now,
		UpdatedAt:    now,
	}
	if err := s.db.WithContext(ctx).Create(row).Error; err != nil {
		return err
	}
	sess.LastActiveAt = row.LastActiveAt
	sess.CreatedAt = row.CreatedAt
	return nil
}

// GetSession 按 id 查询会话，不含软删除记录。
func (s *Store) GetSession(ctx context.Context, id string) (*Session, error) {
	var row sessionRow
	if err := s.db.WithContext(ctx).First(&row, "id = ?", id).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrRecordNotFound
		}
		return nil, err
	}
	return row.toDomain(), nil
}

// GetSessionForUser 查询会话并校验归属。
// 归属不符时返回 ErrRecordNotFound 而非 403，避免泄露「会话存在但不属于你」。
func (s *Store) GetSessionForUser(ctx context.Context, id, userID string) (*Session, error) {
	var row sessionRow
	if err := s.db.WithContext(ctx).First(&row, "id = ? AND user_id = ?", id, userID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrRecordNotFound
		}
		return nil, err
	}
	return row.toDomain(), nil
}

// ListSessions 列出用户的会话，按最近活跃倒序。
func (s *Store) ListSessions(ctx context.Context, userID string, limit int) ([]Session, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	var rows []sessionRow
	if err := s.db.WithContext(ctx).Where("user_id = ?", userID).
		Order("last_active_at DESC").
		Limit(limit).
		Find(&rows).Error; err != nil {
		return nil, err
	}

	out := make([]Session, 0, len(rows))
	for i := range rows {
		out = append(out, *rows[i].toDomain())
	}
	return out, nil
}

// RenameSession 重命名会话（带归属校验）。
func (s *Store) RenameSession(ctx context.Context, id, userID, title string) error {
	res := s.db.WithContext(ctx).Model(&sessionRow{}).
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
func (s *Store) DeleteSession(ctx context.Context, id, userID string) error {
	res := s.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).Delete(&sessionRow{})
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return ErrRecordNotFound
	}
	return nil
}

// TouchSession 更新最近活跃时间。
func (s *Store) TouchSession(ctx context.Context, id string, at time.Time) error {
	return s.db.WithContext(ctx).Model(&sessionRow{}).
		Where("id = ?", id).
		Update("last_active_at", at).Error
}

// UpdateTitle 更新会话标题。
func (s *Store) UpdateTitle(ctx context.Context, sessionID, title string) error {
	return s.db.WithContext(ctx).Model(&sessionRow{}).
		Where("id = ?", sessionID).
		Update("title", title).Error
}

// UpdateSummary 条件更新摘要与游标。
// 用 summary_cursor < cutoff 做条件，防止并发回退（多请求并发时只有前进方向生效）。
func (s *Store) UpdateSummary(ctx context.Context, sessionID, summary string, cursor uint64, contextTokens int) (bool, error) {
	res := s.db.WithContext(ctx).Model(&sessionRow{}).
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

// UpdateContextTokens 记录最近一轮真实上下文用量。
func (s *Store) UpdateContextTokens(ctx context.Context, sessionID string, tokens int) error {
	return s.db.WithContext(ctx).Model(&sessionRow{}).
		Where("id = ?", sessionID).
		Update("context_tokens", tokens).Error
}

// ---------- 消息 ----------

// CreateMessage 插入消息并回填自增 ID。
//
// sessionID 单独传入而非放进 Message：消息本身是纯对话内容，
// 不该为了落库而携带归属字段。tokens 与 meta 由业务层决定（估算或真实用量）。
func (s *Store) CreateMessage(ctx context.Context, sessionID string, m *Message, tokens int, meta MessageMeta) error {
	row := &messageRow{
		SessionID: sessionID,
		Role:      m.Role,
		Content:   m.Content,
		Status:    m.Status,
		Tokens:    tokens,
		Meta:      meta,
	}
	if err := s.db.WithContext(ctx).Create(row).Error; err != nil {
		return err
	}
	m.ID = row.ID
	return nil
}

// ListMessagesAfter 取 id > afterID 的消息（游标之后），按 id 升序。
func (s *Store) ListMessagesAfter(ctx context.Context, sessionID string, afterID uint64) ([]Message, error) {
	var rows []messageRow
	if err := s.db.WithContext(ctx).Where("session_id = ? AND id > ?", sessionID, afterID).
		Order("id ASC").
		Find(&rows).Error; err != nil {
		return nil, err
	}

	out := make([]Message, 0, len(rows))
	for i := range rows {
		out = append(out, rows[i].toDomain())
	}
	return out, nil
}

// CountMessages 统计会话消息条数，用于判断是否首轮。
func (s *Store) CountMessages(ctx context.Context, sessionID string) (int64, error) {
	var n int64
	err := s.db.WithContext(ctx).Model(&messageRow{}).Where("session_id = ?", sessionID).Count(&n).Error
	return n, err
}

// ListMessageViews 游标分页查询历史，返回含 tokens / meta 的完整视图。
// 供前端展示用量与耗时，内部编排不使用它（那里只需要对话内容）。
func (s *Store) ListMessageViews(ctx context.Context, sessionID string, beforeID uint64, limit int) ([]MessageView, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}

	q := s.db.WithContext(ctx).Where("session_id = ?", sessionID)
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
		out = append(out, rows[i].toView())
	}
	return out, nil
}

// reverseRows 原地反转切片。
func reverseRows(rows []messageRow) {
	for i, j := 0, len(rows)-1; i < j; i, j = i+1, j-1 {
		rows[i], rows[j] = rows[j], rows[i]
	}
}
