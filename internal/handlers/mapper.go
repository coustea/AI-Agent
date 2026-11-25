package handlers

import (
	"mentorly/internal/dto"
	"mentorly/internal/service"
	"mentorly/internal/service/auth"
)

func toUserResp(u *auth.User) dto.UserResp {
	return dto.UserResp{ID: u.ID, Username: u.Username, Email: u.Email, Avatar: u.Avatar}
}

func toCredentialResp(c *auth.Credential) dto.LoginResp {
	return dto.LoginResp{Token: c.Token, User: toUserResp(c.User)}
}

func toConversationResp(c *service.Conversation) dto.ConversationResp {
	return dto.ConversationResp{ID: c.ID, Title: c.Title, CreatedAt: c.CreatedAt, UpdatedAt: c.UpdatedAt}
}

func toConversationList(rows []service.Conversation) []dto.ConversationResp {
	out := make([]dto.ConversationResp, 0, len(rows))
	for i := range rows {
		out = append(out, toConversationResp(&rows[i]))
	}
	return out
}

func toMessageList(rows []service.MessageView) []dto.MessageResp {
	out := make([]dto.MessageResp, 0, len(rows))
	for i := range rows {
		m := &rows[i]
		resp := dto.MessageResp{
			ID: m.ID, Role: m.Role, Content: m.Content, Status: m.Status,
			Tokens: m.Tokens, AttachmentIDs: m.AttachmentIDs, CreatedAt: m.CreatedAt,
		}
		// 按消息记录的顺序展开附件，前端直接按数组顺序渲染即可。
		if len(m.Attachments) > 0 {
			resp.Attachments = make([]dto.AttachmentBrief, 0, len(m.Attachments))
			for _, a := range m.Attachments {
				resp.Attachments = append(resp.Attachments, dto.AttachmentBrief{
					ID: a.ID, Filename: a.Filename, Kind: a.Kind, MIME: a.MIME, Size: a.Size,
					DownloadURL: "/api/v1/attachments/" + a.ID + "/download",
				})
			}
		}
		out = append(out, resp)
	}
	return out
}

func toAttachmentResp(a *service.Attachment) dto.AttachmentResp {
	return dto.AttachmentResp{
		ID: a.ID, Filename: a.Filename, Kind: a.Kind, MIME: a.MIME, Size: a.Size,
		TextLength: len([]rune(a.Text)), Truncated: a.Truncated,
		ExtractError: a.ExtractError, DownloadURL: "/api/v1/attachments/" + a.ID + "/download",
	}
}
