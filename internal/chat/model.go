// Package chat 拥有会话与消息的持久化模型和仓储。
//
// 表结构（GORM 行类型）只在本包内可见；对外一律暴露 dialogue 包的领域类型。
// 这样 window / memory / agent 等纯逻辑包不会因为存储细节而依赖 GORM。
package chat

import (
	"time"

	"gorm.io/gorm"

	"mentorly/internal/dialogue"
)

// sessionRow 对应 chat_sessions 表，一条会话一份滚动摘要与两个游标。
//
// 设计要点：
//   - Summary 直接存在于会话行上，不存成 system 消息。一条会话只有一份摘要，
//     消息表因此只保留真实对话，查询与游标推进都更清晰。
//   - SummaryCursor / MemoryCursor 是消息自增 id 的水位线，用于「游标之后的消息」
//     这类查询；推进时用条件更新防止并发回退。
//   - ContextTokens 是最近一轮真实上下文 TotalTokens（含 Prompt），
//     用于下一轮判断是否达压缩阈值。
type sessionRow struct {
	ID     string `gorm:"column:id;type:varchar(36);primaryKey"`
	UserID string `gorm:"column:user_id;type:varchar(36);not null;index:idx_chat_sessions_user,priority:1"`
	Title  string `gorm:"column:title;type:varchar(100);not null;default:'新会话'"`

	Summary       string `gorm:"column:summary;type:text;not null"`
	SummaryCursor uint64 `gorm:"column:summary_cursor;type:bigint unsigned;not null;default:0"`
	MemoryCursor  uint64 `gorm:"column:memory_cursor;type:bigint unsigned;not null;default:0"`
	ContextTokens int    `gorm:"column:context_tokens;type:int;not null;default:0"`

	LastActiveAt time.Time      `gorm:"column:last_active_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);index:idx_chat_sessions_user,priority:3"`
	CreatedAt    time.Time      `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime"`
	UpdatedAt    time.Time      `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime"`
	DeletedAt    gorm.DeletedAt `gorm:"column:deleted_at;type:datetime(3);index:idx_chat_sessions_user,priority:2"`
}

func (sessionRow) TableName() string { return "chat_sessions" }

// toDomain 把存储行转成领域类型。
func (r *sessionRow) toDomain() *dialogue.Session {
	return &dialogue.Session{
		ID:            r.ID,
		UserID:        r.UserID,
		Title:         r.Title,
		Summary:       r.Summary,
		SummaryCursor: r.SummaryCursor,
		MemoryCursor:  r.MemoryCursor,
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
func (r *messageRow) toDomain() dialogue.Message {
	return dialogue.Message{
		ID:      r.ID,
		Role:    r.Role,
		Content: r.Content,
		Status:  r.Status,
	}
}

// MessageMeta 是 chat_messages.meta 的结构。
type MessageMeta struct {
	Usage     *TokenUsage `json:"usage,omitempty"`
	Error     string      `json:"error,omitempty"`
	ElapsedMS int64       `json:"elapsed_ms,omitempty"`
}

// TokenUsage 保存模型返回的真实 token 用量。
type TokenUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// MessageView 是消息的完整视图：领域内容 + 落库时的附加信息。
//
// 为什么不把这些字段放进 dialogue.Message：
// 领域消息只表达「谁说了什么」，而 tokens / usage / error 是存储与观测信息，
// 混进领域模型会让 window、memory 等纯逻辑包携带无关字段。
// 只有历史查询接口需要完整视图，因此单独定义。
type MessageView struct {
	dialogue.Message
	Tokens int
	Meta   MessageMeta
	// CreatedAt 落库时间
	CreatedAt time.Time
}
