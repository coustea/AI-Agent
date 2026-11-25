package tools

import (
	"context"
	"fmt"
	"time"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
)

// ListedAttachment 描述 list_attachments 返回的单条历史附件索引项。
type ListedAttachment struct {
	MessageID    uint64    `json:"message_id"`
	CreatedAt    time.Time `json:"created_at"`
	Question     string    `json:"question"`
	AttachmentID string    `json:"attachment_id"`
	Filename     string    `json:"filename,omitempty"`
	Path         string    `json:"path,omitempty"`
	Status       string    `json:"status"`
}

// NewListAttachments 构造 list_attachments 工具：按消息顺序返回当前会话实际发送过的附件索引。
func NewListAttachments(s *attachments.Store, messages *conversations.Store, principal PrincipalFunc, mountWorkspace string) (tool.InvokableTool, error) {
	if s == nil || messages == nil {
		return nil, fmt.Errorf("附件或会话存储未配置")
	}
	if principal == nil {
		return nil, fmt.Errorf("运行身份解析函数未配置")
	}
	return utils.InferTool(ToolListAttachments,
		"按消息顺序列出当前会话消息实际引用的附件，含关联消息 ID、时间、问题摘要和附件 ID/路径。追问之前上传的附件或上下文压缩后无法定位时使用；再用 read_attachment 读取正文。",
		func(ctx context.Context, _ struct{}) ([]ListedAttachment, error) {
			userID, convID, err := principal(ctx)
			if err != nil {
				return nil, err
			}
			history, err := messages.ListAttachmentMessages(ctx, userID, convID)
			if err != nil {
				return nil, err
			}
			var ids []string
			for _, m := range history {
				ids = append(ids, m.AttachmentIDs...)
			}
			rows, err := s.FindMany(ctx, userID, convID, ids)
			if err != nil {
				return nil, err
			}
			byID := make(map[string]*attachments.Attachment, len(rows))
			for _, a := range rows {
				byID[a.ID] = a
			}
			return attachmentEntries(history, byID, s.Status, mountWorkspace), nil
		})
}

// attachmentEntries 按用户消息与附件 ID 顺序组装列表（严格跟随消息顺序而非上传表主键顺序）。
func attachmentEntries(history []conversations.Message, byID map[string]*attachments.Attachment, statusFn func(*attachments.Attachment) string, mountWorkspace string) []ListedAttachment {
	out := make([]ListedAttachment, 0)
	for _, m := range history {
		if m.Role != conversations.RoleUser {
			continue
		}
		question := truncate(m.Content, 200)
		for _, id := range m.AttachmentIDs {
			entry := ListedAttachment{MessageID: m.ID, CreatedAt: m.CreatedAt, Question: question, AttachmentID: id, Status: "metadata_unavailable"}
			if a := byID[id]; a != nil {
				entry.Filename, entry.Path = a.Filename, attachmentVirtualPath(mountWorkspace, a)
				if statusFn != nil {
					entry.Status = statusFn(a)
				} else {
					entry.Status = "available"
				}
			}
			out = append(out, entry)
		}
	}
	return out
}
