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
)

// Conversation 是用户拥有的会话。
type Conversation struct {
	ID        string
	UserID    string
	Title     string
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Compaction 保存会话最近一次 Eino 上下文压缩检查点。
type Compaction struct {
	Messages       []*schema.Message
	UntilMessageID uint64
}

// CompactionUpdate 描述单轮执行后需要随 SaveRun 原子落库的压缩检查点。
type CompactionUpdate struct {
	Messages              []*schema.Message
	UserMessageID         uint64
	FoldedTranscriptCount int
}

// Message 是一条按 ID 排序的会话消息。
type Message struct {
	ModelMessage  *schema.Message
	ID            uint64
	Role          string
	Content       string
	Status        string
	Tokens        int
	CreatedAt     time.Time
	AttachmentIDs []string
	ToolCalls     []schema.ToolCall
	ToolCallID    string
	ToolName      string
}

const (
	RoleUser        = "user"
	RoleAssistant   = "assistant"
	RoleTool        = "tool"
	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCancelled = "cancelled"
	StatusRunning   = "running"
)

var ErrConversationNotFound = errors.New("会话不存在")

// ErrRecordNotFound 记录不存在，屏蔽 gorm 细节。
var ErrRecordNotFound = errors.New("record not found")

// conversationRow 对应 conversations 表。
//
// 表名从 chat_sessions 改为 conversations：本系统只有一个对话上下文，
// 不必再用 chat_ 前缀区分。迁移脚本负责改名并保留数据。
type conversationRow struct {
	ID                    string            `gorm:"column:id;type:varchar(36);primaryKey"`
	UserID                string            `gorm:"column:user_id;type:varchar(36);not null;index:idx_conversations_user,priority:1"`
	Title                 string            `gorm:"column:title;type:varchar(200);not null;default:'新会话'"`
	SummaryMessages       []*schema.Message `gorm:"column:summary_messages;type:json;serializer:json"`
	SummaryUntilMessageID uint64            `gorm:"column:summary_until_message_id;type:bigint unsigned;not null;default:0"`
	CreatedAt             time.Time         `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime"`
	UpdatedAt             time.Time         `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime;index:idx_conversations_user,priority:2"`
	DeletedAt             gorm.DeletedAt    `gorm:"column:deleted_at;type:datetime(3);index:idx_conversations_user,priority:3"`
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
	ModelMessage   *schema.Message `gorm:"column:model_message;type:json;serializer:json"`
	ID             uint64          `gorm:"column:id;type:bigint unsigned;primaryKey;autoIncrement"`
	ConversationID string          `gorm:"column:conversation_id;type:varchar(36);not null;index:idx_messages_conversation,priority:1"`
	Role           string          `gorm:"column:role;type:varchar(16);not null"`
	Content        string          `gorm:"column:content;type:longtext;not null"`
	Status         string          `gorm:"column:status;type:varchar(16);not null;default:completed"`
	Tokens         int             `gorm:"column:tokens;type:int;not null;default:0"`
	// AttachmentIDs 该消息关联的附件 ID，JSON 列
	AttachmentIDs []string          `gorm:"column:attachment_ids;type:json;serializer:json"`
	ToolCalls     []schema.ToolCall `gorm:"column:tool_calls;type:json;serializer:json"`
	ToolCallID    string            `gorm:"column:tool_call_id;type:varchar(128)"`
	ToolName      string            `gorm:"column:tool_name;type:varchar(128)"`
	CreatedAt     time.Time         `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_messages_conversation,priority:2"`
}

func (messageRow) TableName() string { return "messages" }

func (r *messageRow) toDomain() Message {
	return Message{
		ModelMessage: r.ModelMessage, ID: r.ID,
		Role:          r.Role,
		Content:       r.Content,
		Status:        r.Status,
		Tokens:        r.Tokens,
		CreatedAt:     r.CreatedAt,
		AttachmentIDs: r.AttachmentIDs,
		ToolCalls:     r.ToolCalls,
		ToolCallID:    r.ToolCallID,
		ToolName:      r.ToolName,
	}
}

// Store 是会话与消息的持久化实现。
type Store struct {
	db *gorm.DB
}

// NewStore 构造存储。
func NewStore(db *gorm.DB) *Store { return &Store{db: db} }

// Schema 声明本包拥有的表。
func Schema() []any { return []any{&conversationRow{}, &messageRow{}} }

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

// UpdateTitle 更新标题，调用方须先校验会话归属。
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
		ModelMessage:   m.ModelMessage,
		ConversationID: conversationID,
		Role:           m.Role,
		Content:        m.Content,
		Status:         status,
		Tokens:         m.Tokens,
		AttachmentIDs:  m.AttachmentIDs,
		ToolCalls:      m.ToolCalls,
		ToolCallID:     m.ToolCallID,
		ToolName:       m.ToolName,
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

// GetCompaction 读取会话的上下文压缩检查点。
func (s *Store) GetCompaction(ctx context.Context, conversationID string) (Compaction, error) {
	var row conversationRow
	err := s.db.WithContext(ctx).
		Select("summary_messages", "summary_until_message_id").
		Where("id = ?", conversationID).
		First(&row).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return Compaction{}, ErrConversationNotFound
	}
	if err != nil {
		return Compaction{}, fmt.Errorf("查询压缩检查点失败: %w", err)
	}
	return Compaction{
		Messages:       row.SummaryMessages,
		UntilMessageID: row.SummaryUntilMessageID,
	}, nil
}

func toMessageRow(conversationID string, m Message) messageRow {
	return messageRow{
		ModelMessage:   m.ModelMessage,
		ConversationID: conversationID,
		Role:           m.Role,
		Content:        m.Content,
		Status:         m.Status,
		Tokens:         m.Tokens,
		AttachmentIDs:  m.AttachmentIDs,
		ToolCalls:      m.ToolCalls,
		ToolCallID:     m.ToolCallID,
		ToolName:       m.ToolName,
		CreatedAt:      time.Now(),
	}
}

// SaveRun 原子保存成对工具记录、最终回答及可选的压缩检查点。
func (s *Store) SaveRun(ctx context.Context, conversationID string, transcript []Message, final *Message, compaction *CompactionUpdate) error {
	if final == nil {
		return fmt.Errorf("最终消息不能为空")
	}
	return s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var untilID uint64
		if compaction != nil && len(compaction.Messages) > 0 && compaction.FoldedTranscriptCount == 0 {
			untilID = compaction.UserMessageID
		}
		for i, m := range transcript {
			row := toMessageRow(conversationID, m)
			if err := tx.Create(&row).Error; err != nil {
				return fmt.Errorf("保存运行消息失败: %w", err)
			}
			if compaction != nil && len(compaction.Messages) > 0 && compaction.FoldedTranscriptCount > 0 && i+1 == compaction.FoldedTranscriptCount {
				untilID = row.ID
			}
		}
		finalRow := toMessageRow(conversationID, *final)
		if err := tx.Create(&finalRow).Error; err != nil {
			return fmt.Errorf("保存运行消息失败: %w", err)
		}
		final.ID = finalRow.ID
		final.CreatedAt = finalRow.CreatedAt

		now := time.Now()
		if compaction != nil && len(compaction.Messages) > 0 && untilID > 0 {
			return tx.Model(&conversationRow{}).
				Where("id = ?", conversationID).
				Select("updated_at", "summary_messages", "summary_until_message_id").
				Updates(&conversationRow{
					UpdatedAt:             now,
					SummaryMessages:       compaction.Messages,
					SummaryUntilMessageID: untilID,
				}).Error
		}
		return tx.Model(&conversationRow{}).Where("id = ?", conversationID).Update("updated_at", now).Error
	})
}

// ListMessages 按时间顺序列出消息。
//
// limit <= 0 表示返回全部。原始记录始终完整保留在数据库。
func (s *Store) ListMessages(ctx context.Context, conversationID string, limit int) ([]Message, error) {
	return s.ListMessagesAfter(ctx, conversationID, 0, limit)
}

// ListMessagesAfter 按时间顺序列出 id > afterID 的增量消息。
func (s *Store) ListMessagesAfter(ctx context.Context, conversationID string, afterID uint64, limit int) ([]Message, error) {
	q := s.db.WithContext(ctx).
		Where("conversation_id = ? AND id > ?", conversationID, afterID).
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

// ListVisibleMessages 只返回面向用户的问答，隐藏内部工具记录。
func (s *Store) ListVisibleMessages(ctx context.Context, conversationID string, limit int) ([]Message, error) {
	q := s.db.WithContext(ctx).Where("conversation_id = ? AND (role = ? OR (role = ? AND (tool_calls IS NULL OR JSON_TYPE(tool_calls) = 'NULL' OR JSON_LENGTH(tool_calls) = 0)))", conversationID, RoleUser, RoleAssistant).Order("id ASC")
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

// truncateRunes 按字符截断，避免把多字节字符切断。
func truncateRunes(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}

// ListAttachmentMessages 仅查询本用户会话中真正引用过附件的用户消息。
func (s *Store) ListAttachmentMessages(ctx context.Context, userID, conversationID string) ([]Message, error) {
	var rows []messageRow
	err := s.db.WithContext(ctx).Model(&messageRow{}).
		Select("messages.id, messages.role, messages.content, messages.created_at, messages.attachment_ids").
		Joins("JOIN conversations ON conversations.id = messages.conversation_id AND conversations.deleted_at IS NULL").
		Where("conversations.user_id = ? AND messages.conversation_id = ? AND messages.role = ? AND JSON_LENGTH(messages.attachment_ids) > 0", userID, conversationID, RoleUser).
		Order("messages.id ASC").Find(&rows).Error
	if err != nil {
		return nil, fmt.Errorf("查询附件关联消息失败: %w", err)
	}
	out := make([]Message, 0, len(rows))
	for _, row := range rows {
		out = append(out, row.toDomain())
	}
	return out, nil
}

// FromModel 将框架消息转换为持久化记录，额外字段随原生消息一起保存。
func FromModel(msg *schema.Message, status string) Message {
	if msg == nil {
		msg = schema.AssistantMessage("", nil)
	}
	m := Message{ModelMessage: msg, Role: string(msg.Role), Content: msg.Content, Status: status,
		ToolCalls: msg.ToolCalls, ToolCallID: msg.ToolCallID, ToolName: msg.ToolName}
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
		msg.Role, msg.Content = schema.RoleType(record.Role), record.Content
		msg.ToolCalls, msg.ToolCallID, msg.ToolName = record.ToolCalls, record.ToolCallID, record.ToolName
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
