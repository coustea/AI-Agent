// Package agent 的业务附件工具（list_attachments / read_attachment）与内置外部工具装配。
//
// 职责：
//   - buildBuiltinTools 按固定顺序装配附件查询/分页读取工具，并在搜索凭据齐全时追加 web_search；
//   - list_attachments 按会话消息引用顺序列出附件索引（不返回未发送的孤立上传）；
//   - read_attachment 读取存储层已提取的正文，按 Unicode rune 分页避免切断中文字符。
//
// 安全不变量：
//   - 工具 JSON 入参绝不接受 userID / conversationID，一律通过 PrincipalFrom(ctx) 获取可信身份；
//   - read_attachment 同时校验附件所属用户与当前会话，防止凭附件 ID 跨会话越权读取。
package agent

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/cloudwego/eino/components/tool"
	toolutils "github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
	"mentorly/internal/utils"
)

const (
	toolReadAttachment  = "read_attachment"
	toolListAttachments = "list_attachments"
	toolWebSearch       = "web_search"

	readAttachmentChunkRunes = 20000
	readAttachmentChunkMax   = 50000
)

// buildBuiltinTools 装配外部业务工具列表；缺少搜索凭据时静默跳过 web_search 而非启动失败。
func buildBuiltinTools(atts *attachments.Store, convs *conversations.Store, search SearchConfig) ([]tool.BaseTool, bool, error) {
	readAtt, err := newReadAttachmentTool(atts)
	if err != nil {
		return nil, false, err
	}
	listAtt, err := newListAttachmentsTool(atts, convs)
	if err != nil {
		return nil, false, err
	}
	list := []tool.BaseTool{readAtt, listAtt}

	searchTool, err := newWebSearchTool(search)
	if err != nil {
		return nil, false, err
	}
	if searchTool != nil {
		list = append(list, searchTool)
	}
	return list, searchTool != nil, nil
}

// ---------- list_attachments ----------

// listedAttachment 是历史附件引用索引项，保留消息关联以便上下文摘要后重新定位资料。
type listedAttachment struct {
	MessageID    uint64    `json:"message_id"`
	CreatedAt    time.Time `json:"created_at"`
	Question     string    `json:"question"`
	AttachmentID string    `json:"attachment_id"`
	Filename     string    `json:"filename,omitempty"`
	Path         string    `json:"path,omitempty"`
	Status       string    `json:"status"`
}

func newListAttachmentsTool(s *attachments.Store, messages *conversations.Store) (tool.InvokableTool, error) {
	if s == nil || messages == nil {
		return nil, fmt.Errorf("附件或会话存储未配置")
	}
	return toolutils.InferTool(toolListAttachments,
		"按消息顺序列出当前会话消息实际引用的附件，含关联消息 ID、时间、问题摘要和附件 ID/路径。追问之前上传的附件或上下文压缩后无法定位时使用；再用 read_attachment 读取正文。",
		func(ctx context.Context, _ struct{}) ([]listedAttachment, error) {
			p, err := PrincipalFrom(ctx)
			if err != nil {
				return nil, err
			}
			history, err := messages.ListAttachmentMessages(ctx, p.UserID, p.ConversationID)
			if err != nil {
				return nil, err
			}
			var ids []string
			for _, m := range history {
				ids = append(ids, m.AttachmentIDs...)
			}
			rows, err := s.FindMany(ctx, p.UserID, p.ConversationID, ids)
			if err != nil {
				return nil, err
			}
			byID := make(map[string]*attachments.Attachment, len(rows))
			for _, a := range rows {
				byID[a.ID] = a
			}
			return attachmentEntries(history, byID, s.Status), nil
		})
}

// attachmentEntries 按消息引用顺序输出；即使附件元数据丢失仍保留记录，避免历史引用静默消失。
func attachmentEntries(history []conversations.Message, byID map[string]*attachments.Attachment, statusFn func(*attachments.Attachment) string) []listedAttachment {
	out := make([]listedAttachment, 0)
	for _, m := range history {
		if m.Role != conversations.RoleUser {
			continue
		}
		question := utils.Truncate(m.Content, 200)
		for _, id := range m.AttachmentIDs {
			entry := listedAttachment{MessageID: m.ID, CreatedAt: m.CreatedAt, Question: question, AttachmentID: id, Status: "metadata_unavailable"}
			if a := byID[id]; a != nil {
				entry.Filename, entry.Path = a.Filename, attachmentVirtualPath(a)
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

// ---------- read_attachment ----------

type readAttachmentInput struct {
	AttachmentID string `json:"attachment_id" jsonschema:"description=附件 ID（可在消息里的 attachment 标记或 list_attachments 索引中看到）"`
	Offset       int    `json:"offset,omitempty" jsonschema:"description=从第几个字符开始读，默认 1（首个字符）"`
	Limit        int    `json:"limit,omitempty" jsonschema:"description=本次读取的字符数，默认 20000，上限 50000"`
}

type readAttachmentOutput struct {
	Status       string `json:"status"`
	AttachmentID string `json:"attachment_id"`
	Filename     string `json:"filename"`
	Kind         string `json:"kind"`
	Size         int64  `json:"size"`
	Path         string `json:"path,omitempty"`
	Text         string `json:"text,omitempty"`
	TotalChars   int    `json:"total_chars,omitempty"`
	NextOffset   int    `json:"next_offset,omitempty"`
	Error        string `json:"error,omitempty"`
	Message      string `json:"message"`
}

func newReadAttachmentTool(s *attachments.Store) (tool.InvokableTool, error) {
	if s == nil {
		return nil, fmt.Errorf("附件存储未配置")
	}
	return toolutils.InferTool(toolReadAttachment,
		"读取用户上传附件的正文。当需要回看历史附件、或确认附件状态时使用；长文档按 offset 分页读取。附件 ID 可通过 list_attachments 找回。",
		func(ctx context.Context, in readAttachmentInput) (readAttachmentOutput, error) {
			p, err := PrincipalFrom(ctx)
			if err != nil {
				return readAttachmentOutput{}, err
			}
			id := strings.TrimSpace(in.AttachmentID)
			if id == "" {
				return readAttachmentOutput{}, fmt.Errorf("attachment_id 不能为空")
			}

			a, err := s.GetForUser(ctx, id, p.UserID)
			if errors.Is(err, attachments.ErrNotFound) || (err == nil && a.ConversationID != p.ConversationID) {
				return readAttachmentOutput{AttachmentID: id, Status: "metadata_unavailable", Message: "附件记录不存在或不属于当前用户和会话"}, nil
			}
			if err != nil {
				return readAttachmentOutput{}, err
			}

			out := readAttachmentOutput{
				AttachmentID: a.ID, Status: "ok", Filename: a.Filename,
				Kind: a.Kind, Size: a.Size, Path: attachmentVirtualPath(a),
			}
			if status := s.Status(a); status != "available" {
				out.Status = status
				switch status {
				case "unsupported":
					out.Message = "仅支持 doc、docx、pdf、md 附件"
				case "original_missing":
					out.Error = "附件原件已不存在"
				case "extraction_failed":
					out.Error = "无法提取原件文本"
				default:
					out.Error = "附件原件无法读取"
				}
				if out.Error != "" {
					out.Message = fmt.Sprintf("《%s》：%s。附件引用仍然保留。", a.Filename, out.Error)
				}
				return out, nil
			}

			runes := []rune(a.Text)
			if len(runes) == 0 {
				out.Status, out.Message = "empty", fmt.Sprintf("《%s》没有可提取的文本内容。", a.Filename)
				return out, nil
			}

			out.TotalChars = len(runes)
			chunkText, start, end, nextOffset, err := paginateRunes(runes, in.Offset, in.Limit)
			if err != nil {
				out.Status, out.Message = "invalid_range", fmt.Sprintf("《%s》共 %d 字，%v", a.Filename, len(runes), err)
				return out, nil
			}
			out.Text, out.NextOffset = chunkText, nextOffset
			if nextOffset > 0 {
				out.Message = fmt.Sprintf("已读取《%s》第 %d-%d 字，共 %d 字；后续内容请用 offset=%d 继续读取。", a.Filename, start, end, len(runes), nextOffset)
			} else {
				out.Message = fmt.Sprintf("已读取《%s》第 %d-%d 字，共 %d 字，已到结尾。", a.Filename, start, end, len(runes))
			}
			return out, nil
		})
}

// paginateRunes 使用 1-based Unicode 字符偏移切片，防止把多字节 UTF-8 汉字截断。
func paginateRunes(runes []rune, offset, limit int) (text string, start, end, nextOffset int, err error) {
	if offset < 1 {
		offset = 1
	}
	if offset-1 >= len(runes) {
		return "", 0, 0, 0, fmt.Errorf("offset=%d 已超出范围", offset)
	}
	if limit <= 0 {
		limit = readAttachmentChunkRunes
	}
	if limit > readAttachmentChunkMax {
		limit = readAttachmentChunkMax
	}
	end = min(offset-1+limit, len(runes))
	if end < len(runes) {
		nextOffset = end + 1
	}
	return string(runes[offset-1 : end]), offset, end, nextOffset, nil
}
