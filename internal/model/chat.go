package model

import (
	"time"

	"gorm.io/gorm"
)

// 消息角色
const (
	RoleUser      = "user"
	RoleAssistant = "assistant"
)

// 消息状态：assistant 消息可能因客户端断开或超时未完整生成
const (
	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCancelled = "cancelled"
)

// ChatSession 对应 chat_sessions 表，一条会话一份滚动摘要与两个游标。
//
// 设计要点：
//   - Summary 直接存在于会话行上，不存成 system 消息。一条会话只有一份摘要，
//     消息表因此只保留真实对话，查询与游标推进都更清晰。
//   - SummaryCursor / MemoryCursor 是消息自增 id 的水位线，用于「游标之后的消息」
//     这类查询；推进时用条件更新防止并发回退。
//   - ContextTokens 是最近一轮真实上下文 TotalTokens（含 Prompt），
//     用于下一轮判断是否达压缩阈值。
type ChatSession struct {
	ID     string `gorm:"column:id;type:varchar(36);primaryKey" json:"id"`
	UserID string `gorm:"column:user_id;type:varchar(36);not null;index:idx_chat_sessions_user,priority:1" json:"user_id"`
	Title  string `gorm:"column:title;type:varchar(100);not null;default:'新会话'" json:"title"`

	// Summary 滚动会话摘要，已压缩旧对话的浓缩表达
	Summary string `gorm:"column:summary;type:text;not null" json:"-"`
	// SummaryCursor 已压缩到的消息 id
	SummaryCursor uint64 `gorm:"column:summary_cursor;type:bigint unsigned;not null;default:0" json:"-"`
	// MemoryCursor 已提取长期记忆到的消息 id
	MemoryCursor uint64 `gorm:"column:memory_cursor;type:bigint unsigned;not null;default:0" json:"-"`
	// ContextTokens 最近一轮真实上下文 TotalTokens（含 Prompt）
	ContextTokens int `gorm:"column:context_tokens;type:int;not null;default:0" json:"-"`

	LastActiveAt time.Time      `gorm:"column:last_active_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);index:idx_chat_sessions_user,priority:3" json:"last_active_at"`
	CreatedAt    time.Time      `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime" json:"created_at"`
	UpdatedAt    time.Time      `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime" json:"updated_at"`
	DeletedAt    gorm.DeletedAt `gorm:"column:deleted_at;type:datetime(3);index:idx_chat_sessions_user,priority:2" json:"-"`

	User User `gorm:"foreignKey:UserID;references:ID;constraint:OnDelete:CASCADE;" json:"-"`
}

func (ChatSession) TableName() string { return "chat_sessions" }

// ChatMessage 对应 chat_messages 表。
// ID 使用自增 bigint，因为游标（summary_cursor / memory_cursor）依赖单调递增。
type ChatMessage struct {
	ID        uint64 `gorm:"column:id;type:bigint unsigned;primaryKey;autoIncrement" json:"id"`
	SessionID string `gorm:"column:session_id;type:varchar(36);not null;index:idx_chat_messages_session,priority:1" json:"session_id"`
	Role      string `gorm:"column:role;type:varchar(16);not null" json:"role"`
	Content   string `gorm:"column:content;type:longtext;not null" json:"content"`
	Status    string `gorm:"column:status;type:varchar(16);not null;default:completed" json:"status"`
	// Tokens 写入时估算，assistant 消息可在拿到真实用量后回填 CompletionTokens
	Tokens int `gorm:"column:tokens;type:int;not null;default:0" json:"tokens"`
	// Meta 存放 usage / error / elapsed_ms，用 JSON 列避免频繁加字段
	Meta      MessageMeta `gorm:"column:meta;type:json;serializer:json" json:"meta,omitempty"`
	CreatedAt time.Time   `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_chat_messages_session,priority:2" json:"created_at"`

	Session ChatSession `gorm:"foreignKey:SessionID;references:ID;constraint:OnDelete:CASCADE;" json:"-"`
}

func (ChatMessage) TableName() string { return "chat_messages" }

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

// UserMemory 对应 user_memories 表，每个用户一份 Markdown 记忆文档。
// 用 Version 做乐观锁：并发写入时基于最新版本重试，避免丢失更新。
type UserMemory struct {
	UserID    string    `gorm:"column:user_id;type:varchar(36);primaryKey" json:"user_id"`
	Content   string    `gorm:"column:content;type:mediumtext;not null" json:"content"`
	Version   int       `gorm:"column:version;type:int;not null;default:0" json:"version"`
	UpdatedAt time.Time `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime" json:"updated_at"`
}

func (UserMemory) TableName() string { return "user_memories" }
