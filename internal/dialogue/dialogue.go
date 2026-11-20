// Package dialogue 定义对话的领域模型：消息、轮次、会话视图。
//
// 这是整个系统的中心概念——Agent 围绕「一轮对话」运转，
// 其余各层（存储、窗口裁剪、记忆提取、HTTP）都只是这一轮对话的不同视角。
//
// 本包刻意不依赖任何框架（Gin / GORM / eino），
// 因此可以被任何一层自由引用，也不会造成循环依赖。
package dialogue

import "time"

// 消息角色。
const (
	RoleUser      = "user"
	RoleAssistant = "assistant"
)

// 消息终态。
const (
	// StatusCompleted 正常完成
	StatusCompleted = "completed"
	// StatusFailed 生成失败
	StatusFailed = "failed"
	// StatusCancelled 客户端断开或超时
	StatusCancelled = "cancelled"
)

// Message 是一条对话消息。
//
// 全系统共用这一个结构：存储层写入、窗口裁剪、记忆提取、喂给模型都读它。
// 刻意不再各层各定义一份（旧实现里 agent 与 memory 各有一份同名结构，
// 每跨一层都要写一遍字段拷贝，字段增删要改四处）。
type Message struct {
	// ID 自增主键，同时充当摘要游标与记忆游标的水位线
	ID      uint64
	Role    string
	Content string
	Status  string
}

// IsUser 判断是否用户消息。
func (m Message) IsUser() bool { return m.Role == RoleUser }

// IsAssistant 判断是否助手消息。
func (m Message) IsAssistant() bool { return m.Role == RoleAssistant }

// IsEmptyFailure 判断是否是「生成失败且无内容」的消息。
//
// 这类消息对模型没有信息量，还会破坏 user/assistant 交替结构，
// 因此在裁剪历史与压缩上下文时都要跳过。集中在此处判断，
// 避免各调用点各写一遍条件而出现不一致。
func (m Message) IsEmptyFailure() bool {
	return m.Status == StatusFailed && m.Content == ""
}

// CountTurns 统计 user 消息条数，即「轮数」。
func CountTurns(msgs []Message) int {
	n := 0
	for _, m := range msgs {
		if m.IsUser() {
			n++
		}
	}
	return n
}

// Session 是一轮对话发生其间的会话视图。
//
// 摘要与两个游标挂在会话上而非消息表：一条会话只有一份滚动摘要，
// 消息表因此只保留真实对话，游标推进也更直接。
type Session struct {
	ID     string
	UserID string
	Title  string

	// Summary 滚动摘要，已压缩旧对话的浓缩表达
	Summary string
	// SummaryCursor 已压缩到的消息 id
	SummaryCursor uint64
	// MemoryCursor 已提取长期记忆到的消息 id
	MemoryCursor uint64
	// ContextTokens 最近一轮真实上下文 TotalTokens（含 Prompt）
	ContextTokens int

	LastActiveAt time.Time
	CreatedAt    time.Time
}
