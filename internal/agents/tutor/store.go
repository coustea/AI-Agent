package tutor

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// ErrRecordNotFound 记录不存在，屏蔽 gorm 细节。
var ErrRecordNotFound = errors.New("record not found")

// conversationRow 对应 conversations 表。
//
// 表名从 chat_sessions 改为 conversations：本系统只有一个对话上下文，
// 不必再用 chat_ 前缀区分。迁移脚本负责改名并保留数据。
type conversationRow struct {
	ID        string         `gorm:"column:id;type:varchar(36);primaryKey"`
	UserID    string         `gorm:"column:user_id;type:varchar(36);not null;index:idx_conversations_user,priority:1"`
	Title     string         `gorm:"column:title;type:varchar(200);not null;default:'新会话'"`
	CreatedAt time.Time      `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime"`
	UpdatedAt time.Time      `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime;index:idx_conversations_user,priority:2"`
	DeletedAt gorm.DeletedAt `gorm:"column:deleted_at;type:datetime(3);index:idx_conversations_user,priority:3"`
}

func (conversationRow) TableName() string { return "conversations" }

func (r *conversationRow) toDomain() *Conversation {
	return &Conversation{
		ID:        r.ID,
		UserID:    r.UserID,
		Title:     r.Title,
		CreatedAt: r.CreatedAt,
		UpdatedAt: r.UpdatedAt,
	}
}

// messageRow 对应 messages 表。
//
// ID 用自增 bigint：前端需要稳定的分页游标，
// 而 UUID 不保证单调，做游标分页会漏数据。
type messageRow struct {
	ID             uint64 `gorm:"column:id;type:bigint unsigned;primaryKey;autoIncrement"`
	ConversationID string `gorm:"column:conversation_id;type:varchar(36);not null;index:idx_messages_conversation,priority:1"`
	Role           string `gorm:"column:role;type:varchar(16);not null"`
	Content        string `gorm:"column:content;type:longtext;not null"`
	Status         string `gorm:"column:status;type:varchar(16);not null;default:completed"`
	Tokens         int    `gorm:"column:tokens;type:int;not null;default:0"`
	// AttachmentIDs 该消息关联的附件 ID，JSON 列
	AttachmentIDs []string  `gorm:"column:attachment_ids;type:json;serializer:json"`
	CreatedAt     time.Time `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_messages_conversation,priority:2"`
}

func (messageRow) TableName() string { return "messages" }

func (r *messageRow) toDomain() Message {
	return Message{
		ID:            r.ID,
		Role:          r.Role,
		Content:       r.Content,
		Status:        r.Status,
		Tokens:        r.Tokens,
		CreatedAt:     r.CreatedAt,
		AttachmentIDs: r.AttachmentIDs,
	}
}

// Store 是会话与消息的持久化实现。
type Store struct {
	db *gorm.DB
}

// NewStore 构造存储。
func NewStore(db *gorm.DB) *Store { return &Store{db: db} }

// Schema 声明本包拥有的表。
func (s *Store) Schema() []any { return []any{&conversationRow{}, &messageRow{}} }

// CreateConversation 创建会话。
func (s *Store) CreateConversation(ctx context.Context, userID, title string) (*Conversation, error) {
	if strings.TrimSpace(userID) == "" {
		return nil, fmt.Errorf("用户 ID 不能为空")
	}

	title = strings.TrimSpace(title)
	if title == "" {
		title = "新会话"
	}

	now := time.Now()
	row := &conversationRow{
		ID:     uuid.NewString(),
		UserID: userID,
		Title:  truncateRunes(title, 200),
		// 显式赋值：带 default:CURRENT_TIMESTAMP 的列，
		// gorm 不会在 Create 后回填，响应里会变成 0001-01-01。
		CreatedAt: now,
		UpdatedAt: now,
	}
	if err := s.db.WithContext(ctx).Create(row).Error; err != nil {
		return nil, fmt.Errorf("创建会话失败: %w", err)
	}
	return row.toDomain(), nil
}

// GetConversation 按 ID 取会话并校验归属。
//
// 归属不匹配时返回 ErrConversationNotFound 而不是「无权限」：
// 让调用方无法通过错误差异探测他人会话是否存在。
func (s *Store) GetConversation(ctx context.Context, id, userID string) (*Conversation, error) {
	var row conversationRow
	err := s.db.WithContext(ctx).
		Where("id = ? AND user_id = ?", id, userID).
		First(&row).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrConversationNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}
	return row.toDomain(), nil
}

// ListConversations 列出用户的会话。
func (s *Store) ListConversations(ctx context.Context, userID string, limit int) ([]Conversation, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}

	var rows []conversationRow
	err := s.db.WithContext(ctx).
		Where("user_id = ?", userID).
		Order("updated_at DESC").
		Limit(limit).
		Find(&rows).Error
	if err != nil {
		return nil, fmt.Errorf("查询会话列表失败: %w", err)
	}

	out := make([]Conversation, 0, len(rows))
	for i := range rows {
		out = append(out, *rows[i].toDomain())
	}
	return out, nil
}

// RenameConversation 重命名会话。
func (s *Store) RenameConversation(ctx context.Context, id, userID, title string) error {
	title = strings.TrimSpace(title)
	if title == "" {
		return fmt.Errorf("标题不能为空")
	}

	res := s.db.WithContext(ctx).Model(&conversationRow{}).
		Where("id = ? AND user_id = ?", id, userID).
		Updates(map[string]any{
			"title":      truncateRunes(title, 200),
			"updated_at": time.Now(),
		})
	if res.Error != nil {
		return fmt.Errorf("重命名会话失败: %w", res.Error)
	}
	if res.RowsAffected == 0 {
		return ErrConversationNotFound
	}
	return nil
}

// UpdateTitle 更新标题（异步标题生成用，不做归属校验）。
func (s *Store) UpdateTitle(ctx context.Context, id, title string) error {
	title = strings.TrimSpace(title)
	if title == "" {
		return nil
	}
	return s.db.WithContext(ctx).Model(&conversationRow{}).
		Where("id = ?", id).
		Updates(map[string]any{
			"title":      truncateRunes(title, 200),
			"updated_at": time.Now(),
		}).Error
}

// DeleteConversation 软删除会话。
func (s *Store) DeleteConversation(ctx context.Context, id, userID string) error {
	res := s.db.WithContext(ctx).
		Where("id = ? AND user_id = ?", id, userID).
		Delete(&conversationRow{})
	if res.Error != nil {
		return fmt.Errorf("删除会话失败: %w", res.Error)
	}
	if res.RowsAffected == 0 {
		return ErrConversationNotFound
	}
	return nil
}

// TouchConversation 更新活跃时间。
func (s *Store) TouchConversation(ctx context.Context, id string) error {
	return s.db.WithContext(ctx).Model(&conversationRow{}).
		Where("id = ?", id).
		Update("updated_at", time.Now()).Error
}

// CreateMessage 写入一条消息，回填自增 ID。
func (s *Store) CreateMessage(ctx context.Context, conversationID string, m *Message) error {
	if m == nil {
		return fmt.Errorf("消息不能为空")
	}

	status := m.Status
	if status == "" {
		status = StatusCompleted
	}

	row := &messageRow{
		ConversationID: conversationID,
		Role:           m.Role,
		Content:        m.Content,
		Status:         status,
		Tokens:         m.Tokens,
		AttachmentIDs:  m.AttachmentIDs,
		CreatedAt:      time.Now(),
	}
	if err := s.db.WithContext(ctx).Create(row).Error; err != nil {
		return fmt.Errorf("保存消息失败: %w", err)
	}

	m.ID = row.ID
	m.Status = status
	m.CreatedAt = row.CreatedAt
	return nil
}

// ListMessages 按时间顺序列出消息。
//
// limit <= 0 表示返回全部。历史消息必须完整加载：
// 上下文压缩由官方 Summarization Middleware 在 Agent 内部完成，
// 数据库里的原始记录不会被删除，前端翻历史也就能看到全部内容。
func (s *Store) ListMessages(ctx context.Context, conversationID string, limit int) ([]Message, error) {
	q := s.db.WithContext(ctx).
		Where("conversation_id = ?", conversationID).
		Order("id ASC")
	if limit > 0 {
		q = q.Limit(limit)
	}

	var rows []messageRow
	if err := q.Find(&rows).Error; err != nil {
		return nil, fmt.Errorf("查询消息失败: %w", err)
	}

	out := make([]Message, 0, len(rows))
	for i := range rows {
		out = append(out, rows[i].toDomain())
	}
	return out, nil
}

// CountMessages 统计会话消息数，用于判断是否首轮。
func (s *Store) CountMessages(ctx context.Context, conversationID string) (int64, error) {
	var n int64
	err := s.db.WithContext(ctx).Model(&messageRow{}).
		Where("conversation_id = ?", conversationID).
		Count(&n).Error
	if err != nil {
		return 0, fmt.Errorf("统计消息失败: %w", err)
	}
	return n, nil
}

// truncateRunes 按字符截断，避免把多字节字符切断。
func truncateRunes(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}
