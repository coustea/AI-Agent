package memory

import "context"

// ChatModel 是本包需要的最小 LLM 能力。
// 刻意只保留一个方法：Pre-Run 里的提取与压缩都只需要「给一段文本，拿一段文本」。
// 这样单元测试可以用一个几行的假实现替代真实模型。
type ChatModel interface {
	Complete(ctx context.Context, system, user string) (string, error)
}

// SessionStore 是 memory 包需要的会话读写能力。
// 由 dao 层实现；本包不关心底层是 MySQL 还是内存。
type SessionStore interface {
	// GetSession 读取会话。游标与摘要都挂在这里。
	GetSession(ctx context.Context, sessionID string) (*Session, error)
	// ListMessagesAfter 读取 id > afterID 的消息，升序。
	ListMessagesAfter(ctx context.Context, sessionID string, afterID uint64) ([]Message, error)
	// UpdateSummary 条件推进摘要与游标，返回是否生效。
	UpdateSummary(ctx context.Context, sessionID, summary string, cursor uint64, contextTokens int) (bool, error)
	// AdvanceMemoryCursor 条件推进记忆游标。
	AdvanceMemoryCursor(ctx context.Context, sessionID string, cursor uint64) (bool, error)
}

// MemoryStore 是长期记忆文档的读写能力。
type MemoryStore interface {
	// Get 读取用户记忆文档，不存在时返回空内容与版本 0。
	Get(ctx context.Context, userID string) (*MemoryDoc, error)
	// SaveWithVersion 乐观锁写入，返回是否成功（false 表示版本冲突）。
	SaveWithVersion(ctx context.Context, userID, content string, baseVersion int) (bool, error)
	// Upsert 覆盖写入，用于手动编辑与清空。
	Upsert(ctx context.Context, userID, content string) error
}

// Session 是 memory 包使用的会话视图。
type Session struct {
	ID            string
	UserID        string
	Summary       string
	SummaryCursor uint64
	MemoryCursor  uint64
	ContextTokens int
}

// MemoryDoc 是长期记忆文档。
type MemoryDoc struct {
	UserID  string
	Content string
	Version int
}
