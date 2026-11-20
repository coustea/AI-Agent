package chat

import "time"

// CreateSessionReq 创建会话请求。标题可留空，由首轮回答异步生成。
type CreateSessionReq struct {
	Title string `json:"title" binding:"max=100"`
}

// RenameSessionReq 重命名会话请求。
type RenameSessionReq struct {
	Title string `json:"title" binding:"required,min=1,max=100"`
}

// SessionResp 会话摘要响应。
type SessionResp struct {
	ID           string    `json:"id"`
	Title        string    `json:"title"`
	LastActiveAt time.Time `json:"last_active_at"`
	CreatedAt    time.Time `json:"created_at"`
}

// SendMessageReq 发送消息请求。
type SendMessageReq struct {
	Content string `json:"content" binding:"required,max=20000"`
}

// MessageResp 消息响应。
type MessageResp struct {
	ID        uint64          `json:"id"`
	Role      string          `json:"role"`
	Content   string          `json:"content"`
	Status    string          `json:"status"`
	Tokens    int             `json:"tokens"`
	Meta      *MessageMetaDTO `json:"meta,omitempty"`
	CreatedAt time.Time       `json:"created_at"`
}

// MessageMetaDTO 消息元信息。
type MessageMetaDTO struct {
	PromptTokens     int   `json:"prompt_tokens,omitempty"`
	CompletionTokens int   `json:"completion_tokens,omitempty"`
	TotalTokens      int   `json:"total_tokens,omitempty"`
	ElapsedMS        int64 `json:"elapsed_ms,omitempty"`
}

// toSessionResp 把领域会话转成响应结构。
func toSessionResp(s *Session) SessionResp {
	return SessionResp{
		ID:           s.ID,
		Title:        s.Title,
		LastActiveAt: s.LastActiveAt,
		CreatedAt:    s.CreatedAt,
	}
}

// toSessionList 批量转换会话。
func toSessionList(rows []Session) []SessionResp {
	out := make([]SessionResp, 0, len(rows))
	for i := range rows {
		out = append(out, toSessionResp(&rows[i]))
	}
	return out
}

// toMessageViews 把完整消息视图转成响应，展开 tokens 与 meta。
func toMessageViews(rows []MessageView) []MessageResp {
	out := make([]MessageResp, 0, len(rows))
	for i := range rows {
		m := &rows[i]
		resp := MessageResp{
			ID:        m.ID,
			Role:      m.Role,
			Content:   m.Content,
			Status:    m.Status,
			Tokens:    m.Tokens,
			CreatedAt: m.CreatedAt,
		}
		if m.Meta.Usage != nil || m.Meta.ElapsedMS > 0 {
			meta := &MessageMetaDTO{ElapsedMS: m.Meta.ElapsedMS}
			if m.Meta.Usage != nil {
				meta.PromptTokens = m.Meta.Usage.PromptTokens
				meta.CompletionTokens = m.Meta.Usage.CompletionTokens
				meta.TotalTokens = m.Meta.Usage.TotalTokens
			}
			resp.Meta = meta
		}
		out = append(out, resp)
	}
	return out
}
