package chat

import "time"

// 消息角色。
const (
	// RoleUser 学生发言
	RoleUser = "user"
	// RoleAssistant 辅导员回答
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
// 这是本包的中心类型：存储写入、窗口裁剪、上下文压缩、喂给模型都读它。
// 刻意不携带 SessionID —— 消息本身是纯对话内容，归属由调用点传入，
// 避免为了落库而让领域类型带上冗余字段。
//
// ID 是自增主键，同时充当摘要游标的水位线。
type Message struct {
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

// Session 是一条会话。
//
// 摘要与游标挂在会话上而非消息表：一条会话只有一份滚动摘要，
// 消息表因此只保留真实对话，游标推进也更直接。
type Session struct {
	ID     string
	UserID string
	Title  string

	// Summary 滚动摘要，已压缩旧对话的浓缩表达
	Summary string
	// SummaryCursor 已压缩到的消息 id，是压缩区间的水位线
	SummaryCursor uint64
	// ContextTokens 最近一轮真实上下文 TotalTokens（含 Prompt）
	//
	// 用途是下一轮判断是否达压缩阈值。它必须是模型返回的真实值而非本地估算：
	// eino 会注入约 4.5k token 的工具 Schema 与技能清单，本地估算器完全看不到，
	// 用估算值会让压缩阈值永远打不下来。
	ContextTokens int

	LastActiveAt time.Time
	CreatedAt    time.Time
}

// TokenUsage 是模型返回的真实 token 用量。
type TokenUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// MessageMeta 是消息的附加信息，落库到 chat_messages.meta。
//
// 不并进 Message：这些是存储与观测信息，而 Message 只表达「谁说了什么」。
// 混在一起会让窗口裁剪、上下文压缩等纯逻辑携带无关字段。
type MessageMeta struct {
	Usage     *TokenUsage `json:"usage,omitempty"`
	Error     string      `json:"error,omitempty"`
	ElapsedMS int64       `json:"elapsed_ms,omitempty"`
}

// MessageView 是消息的完整视图：领域内容 + 落库时的附加信息。
// 只有历史查询接口需要它，内部编排只用 Message。
type MessageView struct {
	Message
	Tokens    int
	Meta      MessageMeta
	CreatedAt time.Time
}
