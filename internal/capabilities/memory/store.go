package memory

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// ErrNotFound 记忆不存在或不属于该用户。
// 两种情况返回同一错误，避免通过差异探测他人记忆。
var ErrNotFound = errors.New("memory not found")

// 单条记忆长度上限。记忆应当是一句可复用的事实，而不是一段对话。
const maxContentChars = 500

// memoryRow 对应 memories 表。
//
// 索引设计：user_id 是全部查询的必带条件（用户级隔离），
// 因此所有索引都以 user_id 打头。
type memoryRow struct {
	ID             string    `gorm:"column:id;type:varchar(36);primaryKey"`
	UserID         string    `gorm:"column:user_id;type:varchar(36);not null;index:idx_memories_user,priority:1"`
	Kind           string    `gorm:"column:kind;type:varchar(32);not null;index:idx_memories_user,priority:2"`
	Content        string    `gorm:"column:content;type:varchar(500);not null"`
	Source         string    `gorm:"column:source;type:varchar(16);not null"`
	ConversationID string    `gorm:"column:conversation_id;type:varchar(36);not null"`
	CreatedAt      time.Time `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_memories_user,priority:3"`
	UpdatedAt      time.Time `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime"`
}

func (memoryRow) TableName() string { return "memories" }

func (r *memoryRow) toDomain() *Memory {
	return &Memory{
		ID:             r.ID,
		UserID:         r.UserID,
		Kind:           r.Kind,
		Content:        r.Content,
		Source:         r.Source,
		ConversationID: r.ConversationID,
		CreatedAt:      r.CreatedAt,
		UpdatedAt:      r.UpdatedAt,
	}
}

// Store 是记忆的持久化。
type Store struct {
	db *gorm.DB
}

// NewStore 构造存储。
func NewStore(db *gorm.DB) *Store { return &Store{db: db} }

// Schema 声明本包拥有的表。
func (s *Store) Schema() []any { return []any{&memoryRow{}} }

// Save 写入一条记忆。
//
// 去重策略：同一用户下内容完全相同的记忆不重复写入，
// 直接返回已有记录。这样模型重复调用 save 不会产生冗余条目。
func (s *Store) Save(ctx context.Context, m *Memory) error {
	content := strings.TrimSpace(m.Content)
	if content == "" {
		return fmt.Errorf("记忆内容不能为空")
	}
	if len([]rune(content)) > maxContentChars {
		return fmt.Errorf("记忆内容过长（%d 字），请压缩到 %d 字以内", len([]rune(content)), maxContentChars)
	}
	if strings.TrimSpace(m.UserID) == "" {
		return fmt.Errorf("用户 ID 不能为空")
	}

	// 先查重
	var existing memoryRow
	err := s.db.WithContext(ctx).
		Where("user_id = ? AND content = ?", m.UserID, content).
		First(&existing).Error
	if err == nil {
		*m = *existing.toDomain()
		return nil
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		return fmt.Errorf("查询已有记忆失败: %w", err)
	}

	now := time.Now()
	row := &memoryRow{
		ID:             uuid.NewString(),
		UserID:         m.UserID,
		Kind:           normalizeKind(m.Kind),
		Content:        content,
		Source:         defaultSource(m.Source),
		ConversationID: m.ConversationID,
		CreatedAt:      now,
		UpdatedAt:      now,
	}
	if err := s.db.WithContext(ctx).Create(row).Error; err != nil {
		return fmt.Errorf("保存记忆失败: %w", err)
	}
	*m = *row.toDomain()
	return nil
}

// Search 按关键词检索记忆。
//
// 使用 LIKE 而不是全文索引：记忆条目通常在几十条量级，
// LIKE 完全够用，而引入全文索引会带来中文分词的额外复杂度。
// query 为空时返回最近的记忆，便于 Agent 在会话开始了解用户。
func (s *Store) Search(ctx context.Context, userID, query string, limit int) ([]Memory, error) {
	if strings.TrimSpace(userID) == "" {
		return nil, fmt.Errorf("用户 ID 不能为空")
	}
	if limit <= 0 || limit > 50 {
		limit = 10
	}

	q := s.db.WithContext(ctx).Where("user_id = ?", userID)

	query = strings.TrimSpace(query)
	if query != "" {
		// 多个关键词用空格分隔，任一命中即可（OR），提高召回。
		words := strings.Fields(query)
		if len(words) > 0 {
			clause := s.db
			for i, w := range words {
				pattern := "%" + escapeLike(w) + "%"
				if i == 0 {
					clause = q.Where("content LIKE ? ESCAPE '\\\\'", pattern)
				} else {
					clause = clause.Or("content LIKE ? ESCAPE '\\\\'", pattern)
				}
			}
			q = clause
		}
	}

	var rows []memoryRow
	if err := q.Order("created_at DESC").Limit(limit).Find(&rows).Error; err != nil {
		return nil, fmt.Errorf("检索记忆失败: %w", err)
	}

	out := make([]Memory, 0, len(rows))
	for i := range rows {
		out = append(out, *rows[i].toDomain())
	}
	return out, nil
}

// DeleteForUser 删除一条记忆，带用户归属校验。
func (s *Store) DeleteForUser(ctx context.Context, id, userID string) error {
	res := s.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).Delete(&memoryRow{})
	if res.Error != nil {
		return fmt.Errorf("删除记忆失败: %w", res.Error)
	}
	if res.RowsAffected == 0 {
		return ErrNotFound
	}
	return nil
}

// Count 返回用户记忆条数，用于容量提示。
func (s *Store) Count(ctx context.Context, userID string) (int64, error) {
	var n int64
	err := s.db.WithContext(ctx).Model(&memoryRow{}).Where("user_id = ?", userID).Count(&n).Error
	if err != nil {
		return 0, fmt.Errorf("统计记忆条数失败: %w", err)
	}
	return n, nil
}

func defaultSource(s string) string {
	if s == "explicit" {
		return "explicit"
	}
	return "inferred"
}

// escapeLike 转义 LIKE 的通配符，避免用户输入 % 或 _ 时匹配范围被放大。
func escapeLike(s string) string {
	r := strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`)
	return r.Replace(s)
}
