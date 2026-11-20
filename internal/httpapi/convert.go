// Package httpapi 是 HTTP 传输层。
//
// 它只做四件事：绑定参数、调用领域服务、把事件编码成 SSE、映射状态码。
// 业务规则一律不下沉到这里，传输格式也不上浮到领域层。
package httpapi

import (
	"time"

	"mentorly/internal/chat"
	"mentorly/internal/dialogue"
	"mentorly/internal/httpapi/dto"
	"mentorly/internal/identity"
	"mentorly/internal/memory"
)

// toSessionResp 把领域会话转成响应结构。
func toSessionResp(s *dialogue.Session) dto.SessionResp {
	return dto.SessionResp{
		ID:           s.ID,
		Title:        s.Title,
		LastActiveAt: s.LastActiveAt,
		CreatedAt:    s.CreatedAt,
	}
}

// toSessionList 批量转换会话。
func toSessionList(rows []dialogue.Session) []dto.SessionResp {
	out := make([]dto.SessionResp, 0, len(rows))
	for i := range rows {
		out = append(out, toSessionResp(&rows[i]))
	}
	return out
}

// toMessageResp 把领域消息转成响应结构。
// 领域消息不含 usage / meta，这些是落库时的附加信息，
// 由 chat 层在查询时一并取出（见 httpapi 的历史接口）。
func toMessageResp(m *dialogue.Message) dto.MessageResp {
	return dto.MessageResp{
		ID:      m.ID,
		Role:    m.Role,
		Content: m.Content,
		Status:  m.Status,
	}
}

// toMessageList 批量转换消息。
func toMessageList(rows []dialogue.Message) []dto.MessageResp {
	out := make([]dto.MessageResp, 0, len(rows))
	for i := range rows {
		out = append(out, toMessageResp(&rows[i]))
	}
	return out
}

// toUserResp 转成对外结构，剥离密码哈希等敏感字段。
func toUserResp(u *identity.User) dto.UserResp {
	return dto.UserResp{
		ID:       u.ID,
		Username: u.Username,
		Email:    u.Email,
		Avatar:   u.Avatar,
	}
}

// toCredentialResp 把凭证转成登录响应。
func toCredentialResp(c *identity.Credential) dto.LoginResp {
	return dto.LoginResp{
		Token: c.Token,
		User:  toUserResp(c.User),
	}
}

// toMemoryResp 把记忆文档转成响应。
func toMemoryResp(d *memory.Doc, updatedAt time.Time) dto.MemoryResp {
	return dto.MemoryResp{
		Content:   d.Content,
		Version:   d.Version,
		UpdatedAt: updatedAt,
	}
}

// 编译期断言：确保 chat 与 memory 的类型被正确引用，
// 若这两个包的对外类型改名，这里会立刻编译失败。
var (
	_ = chat.ErrSessionNotFound
	_ = memory.ErrTooLong
)

// toMessageViews 把完整消息视图转成响应，展开 tokens 与 meta。
func toMessageViews(rows []chat.MessageView) []dto.MessageResp {
	out := make([]dto.MessageResp, 0, len(rows))
	for i := range rows {
		m := &rows[i]
		resp := dto.MessageResp{
			ID:        m.ID,
			Role:      m.Role,
			Content:   m.Content,
			Status:    m.Status,
			Tokens:    m.Tokens,
			CreatedAt: m.CreatedAt,
		}
		if m.Meta.Usage != nil || m.Meta.ElapsedMS > 0 {
			meta := &dto.MessageMetaDTO{ElapsedMS: m.Meta.ElapsedMS}
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
