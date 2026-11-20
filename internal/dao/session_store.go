package dao

import (
	"context"
	"time"

	"mentorly/internal/memory"
)

// SessionStore 把 ChatRepo/MemoryRepo 适配成 memory 包所需的接口。
//
// 采用独立适配器而不是给 ChatRepo 堆一堆别名方法：
// memory 包的方法签名（GetSession/ListMessagesAfter/...）与 dao 的业务方法
// 语义不同（前者返回 memory.Session 视图），混在同一个类型里会让 dao 变得
// 难以阅读，也让「谁在调用什么」变模糊。
type SessionStore struct {
	chat *ChatRepo
	mem  *MemoryRepo
}

// NewSessionStore 构造适配器。
func NewSessionStore(chat *ChatRepo, mem *MemoryRepo) *SessionStore {
	return &SessionStore{chat: chat, mem: mem}
}

// 编译期断言。
var (
	_ memory.SessionStore = (*SessionStore)(nil)
	_ memory.MemoryStore  = (*SessionStore)(nil)
)

// GetSession 实现 memory.SessionStore。
func (s *SessionStore) GetSession(ctx context.Context, sessionID string) (*memory.Session, error) {
	row, err := s.chat.GetSession(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	return &memory.Session{
		ID:            row.ID,
		UserID:        row.UserID,
		Summary:       row.Summary,
		SummaryCursor: row.SummaryCursor,
		MemoryCursor:  row.MemoryCursor,
		ContextTokens: row.ContextTokens,
	}, nil
}

// ListMessagesAfter 实现 memory.SessionStore。
func (s *SessionStore) ListMessagesAfter(ctx context.Context, sessionID string, afterID uint64) ([]memory.Message, error) {
	rows, err := s.chat.ListMessagesAfter(ctx, sessionID, afterID)
	if err != nil {
		return nil, err
	}

	out := make([]memory.Message, 0, len(rows))
	for _, m := range rows {
		out = append(out, memory.Message{
			ID:      m.ID,
			Role:    m.Role,
			Content: m.Content,
			Status:  m.Status,
		})
	}
	return out, nil
}

// UpdateSummary 实现 memory.SessionStore。
func (s *SessionStore) UpdateSummary(ctx context.Context, sessionID, summary string, cursor uint64, contextTokens int) (bool, error) {
	return s.chat.UpdateSummary(ctx, sessionID, summary, cursor, contextTokens)
}

// AdvanceMemoryCursor 实现 memory.SessionStore。
func (s *SessionStore) AdvanceMemoryCursor(ctx context.Context, sessionID string, cursor uint64) (bool, error) {
	return s.chat.AdvanceMemoryCursor(ctx, sessionID, cursor)
}

// Get 实现 memory.MemoryStore。
func (s *SessionStore) Get(ctx context.Context, userID string) (*memory.MemoryDoc, error) {
	row, err := s.mem.Get(ctx, userID)
	if err != nil {
		return nil, err
	}
	return &memory.MemoryDoc{
		UserID:  row.UserID,
		Content: row.Content,
		Version: row.Version,
	}, nil
}

// SaveWithVersion 实现 memory.MemoryStore。
func (s *SessionStore) SaveWithVersion(ctx context.Context, userID, content string, baseVersion int) (bool, error) {
	return s.mem.SaveWithVersion(ctx, userID, content, baseVersion)
}

// Upsert 实现 memory.MemoryStore。
func (s *SessionStore) Upsert(ctx context.Context, userID, content string) error {
	return s.mem.Upsert(ctx, userID, content)
}

// AppendPending 实现 agent.MemoryAppender：把 remember 工具的一条记录追加到
// 用户记忆文档的「待整合」小节，等下次 Pre-Run 整合时并入正式章节。
func (s *SessionStore) AppendPending(ctx context.Context, userID, note string) error {
	doc, err := s.mem.Get(ctx, userID)
	if err != nil {
		return err
	}

	updated := memory.AppendPending(doc.Content, note, nowDate())
	return s.mem.Upsert(ctx, userID, updated)
}

// nowDate 返回记忆条目使用的短日期。
func nowDate() string {
	return time.Now().Format("2006-01-02")
}
