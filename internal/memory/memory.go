// Package memory 管理跨会话的长期记忆：从对话中提炼学生画像与学习进展，
// 维护成一份持久化的 Markdown 文档，在下一轮对话前注入 System Prompt。
//
// 与 window 包的分工：
//   - window 处理「这一次能带多少历史」，是单会话内的短期窗口；
//   - memory 处理「跨会话要记住什么」，是跨会话的长期沉淀。
//
// 两者都只在 Pre-Run 阶段被 turn 调用，互不依赖。
package memory

import (
	"context"
	"time"

	"mentorly/internal/dialogue"
)

// ChatModel 是本包需要的最小 LLM 能力。
// 刻意只保留一个方法：记忆整合只需要「给一段文本，拿一段文本」。
// 这样单元测试可以用一个几行的假实现替代真实模型。
type ChatModel interface {
	Complete(ctx context.Context, system, user string) (string, error)
}

// Store 是长期记忆文档的读写能力。
type Store interface {
	// Get 读取用户记忆文档，不存在时返回空内容与版本 0。
	Get(ctx context.Context, userID string) (*Doc, error)
	// SaveWithVersion 乐观锁写入，返回是否成功（false 表示版本冲突）。
	SaveWithVersion(ctx context.Context, userID, content string, baseVersion int) (bool, error)
	// Upsert 覆盖写入，用于手动编辑与清空。
	Upsert(ctx context.Context, userID, content string) error
}

// Recorder 记录「待整合」条目，由 remember 工具调用。
// 定义在 memory 包内，使 agent 只依赖这个窄接口。
type Recorder interface {
	// AppendPending 把一条记录追加到用户记忆文档的待整合小节。
	AppendPending(ctx context.Context, userID, note string) error
}

// Transcript 是会话消息的只读视图，供整合器读取「尚未提取的对话」。
//
// 只包含整合真正需要的两个方法，而不是整个会话仓储：
// 整合器不需要写消息、不需要改标题，给它更多能力只会让依赖关系模糊。
type Transcript interface {
	// Session 读取会话游标与用户归属。
	Session(ctx context.Context, sessionID string) (*dialogue.Session, error)
	// MessagesAfter 读取 id > afterID 的消息，升序。
	MessagesAfter(ctx context.Context, sessionID string, afterID uint64) ([]dialogue.Message, error)
	// UpdateSummary 条件推进摘要与游标，返回是否生效。
	UpdateSummary(ctx context.Context, sessionID, summary string, cursor uint64, contextTokens int) (bool, error)
	// AdvanceMemoryCursor 条件推进记忆游标。
	AdvanceMemoryCursor(ctx context.Context, sessionID string, cursor uint64) (bool, error)
}

// Doc 是长期记忆文档。
type Doc struct {
	UserID  string
	Content string
	Version int
}

// Config 是记忆策略的可调参数。
type Config struct {
	// MinTurns 触发提取的未提取轮数阈值
	MinTurns int
	// MinTokens 触发提取的未提取 token 阈值
	MinTokens int
	// MaxChars 记忆文档最大字符数
	MaxChars int
	// Timeout 单次 LLM 调用（整合）超时
	Timeout time.Duration
}

// withDefaults 填充零值，避免测试与生产因零值永远不触发。
func (c Config) withDefaults() Config {
	if c.MinTurns <= 0 {
		c.MinTurns = 4
	}
	if c.MinTokens <= 0 {
		c.MinTokens = 4000
	}
	if c.MaxChars <= 0 {
		c.MaxChars = 2000
	}
	if c.Timeout <= 0 {
		c.Timeout = 120 * time.Second
	}
	return c
}
