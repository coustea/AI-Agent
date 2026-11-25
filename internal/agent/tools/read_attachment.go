package tools

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/repository/attachments"
)

const (
	readAttachmentChunkRunes = 20000
	readAttachmentChunkMax   = 50000
)

// ReadAttachmentInput 是 read_attachment 工具的入参。
type ReadAttachmentInput struct {
	AttachmentID string `json:"attachment_id" jsonschema:"description=附件 ID，形如 att_xxx，可在消息里的 attachment 标记或附件索引中看到"`
	Offset       int    `json:"offset,omitempty" jsonschema:"description=从第几个字符开始读，默认 1（首个字符）。用于分页读取长文档"`
	Limit        int    `json:"limit,omitempty" jsonschema:"description=本次读取的字符数，默认 20000，上限 50000"`
}

// ReadAttachmentOutput 是 read_attachment 工具的结构化返回值。
type ReadAttachmentOutput struct {
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

// NewReadAttachment 构造 read_attachment 工具：校验归属后按字符分页读取附件原文。
func NewReadAttachment(s *attachments.Store, principal PrincipalFunc, mountWorkspace string) (tool.InvokableTool, error) {
	if s == nil {
		return nil, fmt.Errorf("附件存储未配置")
	}
	if principal == nil {
		return nil, fmt.Errorf("运行身份解析函数未配置")
	}
	return utils.InferTool(ToolReadAttachment,
		"读取用户上传附件的正文。当需要回看历史附件、或确认附件状态时使用；长文档按 offset 分页读取。附件 ID 可通过 list_attachments 找回。",
		func(ctx context.Context, in ReadAttachmentInput) (ReadAttachmentOutput, error) {
			userID, convID, err := principal(ctx)
			if err != nil {
				return ReadAttachmentOutput{}, err
			}
			id := strings.TrimSpace(in.AttachmentID)
			if id == "" {
				return ReadAttachmentOutput{}, fmt.Errorf("attachment_id 不能为空")
			}

			a, err := s.GetForUser(ctx, id, userID)
			if errors.Is(err, attachments.ErrNotFound) || (err == nil && a.ConversationID != convID) {
				return ReadAttachmentOutput{AttachmentID: id, Status: "metadata_unavailable", Message: "附件记录不存在或不属于当前用户和会话"}, nil
			}
			if err != nil {
				return ReadAttachmentOutput{}, err
			}

			out := ReadAttachmentOutput{
				AttachmentID: a.ID, Status: "ok", Filename: a.Filename,
				Kind: a.Kind, Size: a.Size, Path: attachmentVirtualPath(mountWorkspace, a),
			}
			if !attachments.Supported(a.Ext) {
				out.Status, out.Message = "unsupported", "仅支持 doc、docx、pdf、md 附件"
				return out, nil
			}

			text, err := s.FullText(ctx, a)
			if err != nil {
				out.Status, out.Error = "extraction_failed", "无法提取原件文本"
				if errors.Is(err, os.ErrNotExist) {
					out.Status, out.Error = "original_missing", "附件原件已不存在"
				} else if varErr := (*os.PathError)(nil); errors.As(err, &varErr) {
					out.Status, out.Error = "read_failed", "附件原件无法读取"
				}
				out.Message = fmt.Sprintf("《%s》：%s。附件引用仍然保留。", a.Filename, out.Error)
				return out, nil
			}

			runes := []rune(text)
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

// paginateRunes 按 1-based rune 偏移量切片文本，并将单次读取量钳制在 [1, readAttachmentChunkMax]。
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
