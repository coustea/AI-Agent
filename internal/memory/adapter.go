package memory

import (
	"context"
	"time"

	"mentorly/internal/chat"
	"mentorly/internal/dialogue"
)

// Adapters 把 chat 仓储与记忆仓储适配成 memory 包所需的窄接口。
//
// 放在 memory 包内（而不是 chat 或 platform/store）是为了让依赖方向保持单向：
// memory 定义自己需要什么，chat 完全不知道 memory 的存在。
// 旧实现把适配器放在 dao 包，导致 dao → memory 的反向依赖。
type Adapters struct {
	sessions *chat.Repo
	store    *Repo
}

// NewAdapters 构造适配器集合。
func NewAdapters(sessions *chat.Repo, store *Repo) *Adapters {
	return &Adapters{sessions: sessions, store: store}
}

// 编译期断言。
var (
	_ Transcript = (*Adapters)(nil)
	_ Store      = (*Adapters)(nil)
	_ Recorder   = (*Adapters)(nil)
)

// Session 实现 Transcript。
func (a *Adapters) Session(ctx context.Context, sessionID string) (*dialogue.Session, error) {
	row, err := a.sessions.GetSession(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	return &dialogue.Session{
		ID:            row.ID,
		UserID:        row.UserID,
		Title:         row.Title,
		Summary:       row.Summary,
		SummaryCursor: row.SummaryCursor,
		MemoryCursor:  row.MemoryCursor,
		ContextTokens: row.ContextTokens,
		LastActiveAt:  row.LastActiveAt,
		CreatedAt:     row.CreatedAt,
	}, nil
}

// MessagesAfter 实现 Transcript。
func (a *Adapters) MessagesAfter(ctx context.Context, sessionID string, afterID uint64) ([]dialogue.Message, error) {
	rows, err := a.sessions.ListMessagesAfter(ctx, sessionID, afterID)
	if err != nil {
		return nil, err
	}

	out := make([]dialogue.Message, 0, len(rows))
	for _, m := range rows {
		out = append(out, dialogue.Message{
			ID:      m.ID,
			Role:    m.Role,
			Content: m.Content,
			Status:  m.Status,
		})
	}
	return out, nil
}

// UpdateSummary 实现 Transcript。
func (a *Adapters) UpdateSummary(ctx context.Context, sessionID, summary string, cursor uint64, contextTokens int) (bool, error) {
	return a.sessions.UpdateSummary(ctx, sessionID, summary, cursor, contextTokens)
}

// AdvanceMemoryCursor 实现 Transcript。
func (a *Adapters) AdvanceMemoryCursor(ctx context.Context, sessionID string, cursor uint64) (bool, error) {
	return a.sessions.AdvanceMemoryCursor(ctx, sessionID, cursor)
}

// Get 实现 Store。
func (a *Adapters) Get(ctx context.Context, userID string) (*Doc, error) {
	row, err := a.store.Get(ctx, userID)
	if err != nil {
		return nil, err
	}
	return &Doc{UserID: row.UserID, Content: row.Content, Version: row.Version}, nil
}

// SaveWithVersion 实现 Store。
func (a *Adapters) SaveWithVersion(ctx context.Context, userID, content string, baseVersion int) (bool, error) {
	return a.store.SaveWithVersion(ctx, userID, content, baseVersion)
}

// Upsert 实现 Store。
func (a *Adapters) Upsert(ctx context.Context, userID, content string) error {
	return a.store.Upsert(ctx, userID, content)
}

// AppendPending 实现 Recorder：把 remember 工具的一条记录追加到
// 用户记忆文档的「待整合」小节，等下次 Pre-Run 整合时并入正式章节。
func (a *Adapters) AppendPending(ctx context.Context, userID, note string) error {
	doc, err := a.store.Get(ctx, userID)
	if err != nil {
		return err
	}
	updated := AppendPending(doc.Content, note, time.Now().Format("2006-01-02"))
	return a.store.Upsert(ctx, userID, updated)
}
