package conversations

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/cloudwego/eino/schema"
	"github.com/google/uuid"
	"gorm.io/gorm"

	"mentorly/internal/utils"
)

const (
	RoleUser        = "user"
	RoleAssistant   = "assistant"
	RoleTool        = "tool"
	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCancelled = "cancelled"
)

var ErrConversationNotFound = errors.New("会话不存在")

// Conversation 对应 conversations 表。
type Conversation struct {
	ID                    string            `gorm:"column:id;type:varchar(36);primaryKey"`
	UserID                string            `gorm:"column:user_id;type:varchar(36);not null;index:idx_conversations_user,priority:1"`
	Title                 string            `gorm:"column:title;type:varchar(200);not null;default:'新会话'"`
	SummaryMessages       []*schema.Message `gorm:"column:summary_messages;type:json;serializer:json" json:"-"`
	SummaryUntilMessageID uint64            `gorm:"column:summary_until_message_id;type:bigint unsigned;not null;default:0" json:"-"`
	CreatedAt             time.Time         `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime"`
	UpdatedAt             time.Time         `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime;index:idx_conversations_user,priority:2"`
	DeletedAt             gorm.DeletedAt    `gorm:"column:deleted_at;type:datetime(3);index:idx_conversations_user,priority:3" json:"-"`
}

func (Conversation) TableName() string { return "conversations" }

// Compaction 保存会话最近一次 Eino 上下文压缩检查点。
type Compaction struct {
	Messages       []*schema.Message
	UntilMessageID uint64
}

// CompactionUpdate 描述单轮执行后需要随 SaveRun 原子落库的压缩检查点。
type CompactionUpdate struct {
	Messages      []*schema.Message
	UserMessageID uint64
	// 包括摘要和保留消息共同覆盖的原始记录数。
	CoveredTranscriptCount int
}

// Message 对应 messages 表；ModelMessage 完整保存原生 Eino 协议字段，Visible 区分面向用户的问答与内部工具轨迹。
type Message struct {
	ID             uint64          `gorm:"column:id;type:bigint unsigned;primaryKey;autoIncrement"`
	ConversationID string          `gorm:"column:conversation_id;type:varchar(36);not null;index:idx_messages_conv_vis,priority:1"`
	Visible        bool            `gorm:"column:visible;type:tinyint(1);not null;default:1;index:idx_messages_conv_vis,priority:2"`
	Role           string          `gorm:"column:role;type:varchar(16);not null"`
	Content        string          `gorm:"column:content;type:longtext;not null"`
	Status         string          `gorm:"column:status;type:varchar(16);not null;default:completed"`
	Tokens         int             `gorm:"column:tokens;type:int;not null;default:0"`
	AttachmentIDs  []string        `gorm:"column:attachment_ids;type:json;serializer:json"`
	ModelMessage   *schema.Message `gorm:"column:model_message;type:json;serializer:json"`
	CreatedAt      time.Time       `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_messages_conv_vis,priority:3"`
}

func (Message) TableName() string { return "messages" }

type Store struct {
	db *gorm.DB
}

func NewStore(db *gorm.DB) *Store { return &Store{db: db} }

func Schema() []any { return []any{&Conversation{}, &Message{}} }

func (s *Store) CreateConversation(ctx context.Context, userID, title string) (*Conversation, error) {
	if strings.TrimSpace(userID) == "" {
		return nil, fmt.Errorf("用户 ID 不能为空")
	}
	title = strings.TrimSpace(title)
	if title == "" {
		title = "新会话"
	}
	now := time.Now()
	conv := &Conversation{
		ID:        uuid.NewString(),
		UserID:    userID,
		Title:     utils.ClipRunes(title, 200),
		CreatedAt: now,
		UpdatedAt: now,
	}
	if err := s.db.WithContext(ctx).Create(conv).Error; err != nil {
		return nil, fmt.Errorf("创建会话失败: %w", err)
	}
	return conv, nil
}

// GetConversation 按 ID 取会话并校验归属；归属不匹配统一返回 ErrConversationNotFound。
func (s *Store) GetConversation(ctx context.Context, id, userID string) (*Conversation, error) {
	var conv Conversation
	err := s.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).First(&conv).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrConversationNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}
	return &conv, nil
}

func (s *Store) ListConversations(ctx context.Context, userID string, limit int) ([]Conversation, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	var out []Conversation
	err := s.db.WithContext(ctx).
		Where("user_id = ?", userID).
		Order("updated_at DESC").
		Limit(limit).
		Find(&out).Error
	if err != nil {
		return nil, fmt.Errorf("查询会话列表失败: %w", err)
	}
	return out, nil
}

func (s *Store) RenameConversation(ctx context.Context, id, userID, title string) error {
	title = strings.TrimSpace(title)
	if title == "" {
		return fmt.Errorf("标题不能为空")
	}
	res := s.db.WithContext(ctx).Model(&Conversation{}).
		Where("id = ? AND user_id = ?", id, userID).
		Updates(map[string]any{
			"title":      utils.ClipRunes(title, 200),
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

func (s *Store) UpdateTitle(ctx context.Context, id, title string) error {
	title = strings.TrimSpace(title)
	if title == "" {
		return nil
	}
	return s.db.WithContext(ctx).Model(&Conversation{}).
		Where("id = ?", id).
		Updates(map[string]any{
			"title":      utils.ClipRunes(title, 200),
			"updated_at": time.Now(),
		}).Error
}

func (s *Store) DeleteConversation(ctx context.Context, id, userID string) error {
	res := s.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).Delete(&Conversation{})
	if res.Error != nil {
		return fmt.Errorf("删除会话失败: %w", res.Error)
	}
	if res.RowsAffected == 0 {
		return ErrConversationNotFound
	}
	return nil
}

func (s *Store) TouchConversation(ctx context.Context, id string) error {
	return s.db.WithContext(ctx).Model(&Conversation{}).Where("id = ?", id).Update("updated_at", time.Now()).Error
}

func (s *Store) CreateMessage(ctx context.Context, conversationID string, m *Message) error {
	if m == nil {
		return fmt.Errorf("消息不能为空")
	}
	m.ConversationID = conversationID
	if m.Status == "" {
		m.Status = StatusCompleted
	}
	if m.CreatedAt.IsZero() {
		m.CreatedAt = time.Now()
	}
	if err := s.db.WithContext(ctx).Create(m).Error; err != nil {
		return fmt.Errorf("保存消息失败: %w", err)
	}
	return nil
}

func (s *Store) GetCompaction(ctx context.Context, conversationID string) (Compaction, error) {
	var conv Conversation
	err := s.db.WithContext(ctx).
		Select("summary_messages", "summary_until_message_id").
		Where("id = ?", conversationID).
		First(&conv).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return Compaction{}, ErrConversationNotFound
	}
	if err != nil {
		return Compaction{}, fmt.Errorf("查询压缩检查点失败: %w", err)
	}
	return Compaction{
		Messages:       conv.SummaryMessages,
		UntilMessageID: conv.SummaryUntilMessageID,
	}, nil
}

// SaveRun 原子保存成对工具记录、最终回答及可选的压缩检查点。
func (s *Store) SaveRun(ctx context.Context, conversationID string, transcript []Message, final *Message, compaction *CompactionUpdate) error {
	if final == nil {
		return fmt.Errorf("最终消息不能为空")
	}
	return s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var untilID uint64
		if compaction != nil && len(compaction.Messages) > 0 && compaction.CoveredTranscriptCount == 0 {
			untilID = compaction.UserMessageID
		}
		for i := range transcript {
			row := transcript[i]
			row.ConversationID = conversationID
			row.Visible = false
			row.CreatedAt = time.Now()
			if err := tx.Create(&row).Error; err != nil {
				return fmt.Errorf("保存运行消息失败: %w", err)
			}
			if compaction != nil && len(compaction.Messages) > 0 && compaction.CoveredTranscriptCount > 0 && i+1 == compaction.CoveredTranscriptCount {
				untilID = row.ID
			}
		}
		final.ConversationID = conversationID
		final.Visible = true
		final.CreatedAt = time.Now()
		if err := tx.Create(final).Error; err != nil {
			return fmt.Errorf("保存运行消息失败: %w", err)
		}

		now := time.Now()
		if compaction != nil && len(compaction.Messages) > 0 && untilID > 0 {
			return tx.Model(&Conversation{}).
				Where("id = ?", conversationID).
				Select("updated_at", "summary_messages", "summary_until_message_id").
				Updates(&Conversation{
					UpdatedAt:             now,
					SummaryMessages:       compaction.Messages,
					SummaryUntilMessageID: untilID,
				}).Error
		}
		return tx.Model(&Conversation{}).Where("id = ?", conversationID).Update("updated_at", now).Error
	})
}

func (s *Store) ListMessagesAfter(ctx context.Context, conversationID string, afterID uint64, limit int) ([]Message, error) {
	q := s.db.WithContext(ctx).Where("conversation_id = ? AND id > ?", conversationID, afterID).Order("id ASC")
	if limit > 0 {
		q = q.Limit(limit)
	}
	var out []Message
	if err := q.Find(&out).Error; err != nil {
		return nil, fmt.Errorf("查询消息失败: %w", err)
	}
	return out, nil
}

// ListVisibleMessages 只返回面向用户的问答，隐藏内部工具轨迹。
func (s *Store) ListVisibleMessages(ctx context.Context, conversationID string, limit int) ([]Message, error) {
	q := s.db.WithContext(ctx).Where("conversation_id = ? AND visible = ?", conversationID, true).Order("id ASC")
	if limit > 0 {
		q = q.Limit(limit)
	}
	var out []Message
	if err := q.Find(&out).Error; err != nil {
		return nil, fmt.Errorf("查询消息失败: %w", err)
	}
	return out, nil
}

func (s *Store) ListAttachmentMessages(ctx context.Context, userID, conversationID string) ([]Message, error) {
	var out []Message
	err := s.db.WithContext(ctx).Model(&Message{}).
		Select("messages.id, messages.role, messages.content, messages.created_at, messages.attachment_ids").
		Joins("JOIN conversations ON conversations.id = messages.conversation_id AND conversations.deleted_at IS NULL").
		Where("conversations.user_id = ? AND messages.conversation_id = ? AND messages.role = ? AND JSON_LENGTH(messages.attachment_ids) > 0", userID, conversationID, RoleUser).
		Order("messages.id ASC").Find(&out).Error
	if err != nil {
		return nil, fmt.Errorf("查询附件关联消息失败: %w", err)
	}
	return out, nil
}

// FromModel 将框架消息转换为持久化记录。
func FromModel(msg *schema.Message, status string, visible bool) Message {
	if msg == nil {
		msg = schema.AssistantMessage("", nil)
	}
	m := Message{
		ModelMessage: msg,
		Visible:      visible,
		Role:         string(msg.Role),
		Content:      msg.Content,
		Status:       status,
	}
	if msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil {
		m.Tokens = msg.ResponseMeta.Usage.CompletionTokens
	}
	return m
}

// ModelMessages 在读取边界恢复多轮模型消息：推理过程留库但不带入后续轮次。
func ModelMessages(history []Message) []*schema.Message {
	out := make([]*schema.Message, 0, len(history))
	for _, record := range history {
		var msg schema.Message
		if record.ModelMessage != nil {
			msg = *record.ModelMessage
		}
		if msg.Role == "" {
			msg.Role = schema.RoleType(record.Role)
		}
		if record.Content != "" {
			msg.Content = record.Content
		}
		msg.ReasoningContent = ""
		if len(msg.AssistantGenMultiContent) > 0 {
			filtered := make([]schema.MessageOutputPart, 0, len(msg.AssistantGenMultiContent))
			for _, part := range msg.AssistantGenMultiContent {
				if part.Type != schema.ChatMessagePartTypeReasoning {
					filtered = append(filtered, part)
				}
			}
			msg.AssistantGenMultiContent = filtered
		}
		if strings.TrimSpace(msg.Content) == "" && len(msg.ToolCalls) == 0 && msg.ToolCallID == "" && len(msg.UserInputMultiContent) == 0 && len(msg.AssistantGenMultiContent) == 0 {
			continue
		}
		out = append(out, &msg)
	}
	return out
}
