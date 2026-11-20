package attachments

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/runtime"
)

// 工具名。
const (
	ReadToolName = "read_attachment"
	ListToolName = "list_attachments"
)

// ---------- read_attachment ----------

// ReadInput 是 read_attachment 参数。
type ReadInput struct {
	AttachmentID string `json:"attachment_id" jsonschema:"description=附件 ID，由用户消息中给出，形如 att_xxx"`
}

// ReadOutput 是 read_attachment 返回。
type ReadOutput struct {
	AttachmentID string `json:"attachment_id"`
	Filename     string `json:"filename"`
	Kind         string `json:"kind"`
	Size         int64  `json:"size"`
	// Text 提取出的正文（文档类）
	Text string `json:"text,omitempty"`
	// Truncated 文本是否被截断
	Truncated bool `json:"truncated,omitempty"`
	// Image 为 true 表示这是图片，正文由模型直接看到，无需读文本
	Image   bool   `json:"image,omitempty"`
	Error   string `json:"error,omitempty"`
	Message string `json:"message"`
}

// NewReadTool 构造附件读取工具。
//
// 图片类附件在消息里已经以多模态形式直传，模型能直接看到，
// 因此这里对图片只返回元信息，避免重复塞入二进制。
func NewReadTool(s *Store) (tool.InvokableTool, error) {
	if s == nil {
		return nil, fmt.Errorf("附件存储未配置")
	}

	return utils.InferTool(ReadToolName,
		"读取用户上传的附件内容。当用户消息提到附件、或你需要查看文档内容时使用。"+
			"图片已在对话中直接可见，无需读取；PDF/Word/PPT/文本文件需要用本工具读取正文。",
		func(ctx context.Context, in ReadInput) (ReadOutput, error) {
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return ReadOutput{}, err
			}

			id := strings.TrimSpace(in.AttachmentID)
			if id == "" {
				return ReadOutput{}, fmt.Errorf("attachment_id 不能为空")
			}

			a, err := s.GetForUser(ctx, id, p.UserID)
			if err != nil {
				if err == ErrNotFound {
					return ReadOutput{}, fmt.Errorf("未找到该附件，或它不属于当前用户")
				}
				return ReadOutput{}, err
			}

			out := ReadOutput{
				AttachmentID: a.ID,
				Filename:     a.Filename,
				Kind:         a.Kind,
				Size:         a.Size,
			}

			if a.NativeImage() {
				out.Image = true
				out.Message = fmt.Sprintf("《%s》是图片，内容已在对话中直接可见。", a.Filename)
				return out, nil
			}

			if a.ExtractError != "" {
				// 提取失败必须如实上报，让模型据此告知用户，
				// 而不是把「读取失败」当成「文件为空」。
				out.Error = a.ExtractError
				out.Message = fmt.Sprintf("《%s》无法解析：%s", a.Filename, a.ExtractError)
				return out, nil
			}

			if strings.TrimSpace(a.Text) == "" {
				out.Message = fmt.Sprintf("《%s》没有可提取的文本内容。", a.Filename)
				return out, nil
			}

			out.Text = a.Text
			out.Truncated = a.Truncated
			out.Message = fmt.Sprintf("已读取《%s》，共 %d 字。", a.Filename, len([]rune(a.Text)))
			if a.Truncated {
				out.Message += " 内容较长，已截断。"
			}
			return out, nil
		})
}

// ---------- list_attachments ----------

// ListInput 是 list_attachments 参数。
type ListInput struct {
	// 无需参数：会话由运行上下文提供
	_ struct{} `json:"-"`
}

// AttachmentItem 是附件列表项。
type AttachmentItem struct {
	ID       string `json:"id"`
	Filename string `json:"filename"`
	Kind     string `json:"kind"`
	Size     int64  `json:"size"`
}

// ListOutput 是 list_attachments 返回。
type ListOutput struct {
	Count   int              `json:"count"`
	Items   []AttachmentItem `json:"items"`
	Message string           `json:"message"`
}

// NewListTool 构造附件列表工具。
func NewListTool(s *Store) (tool.InvokableTool, error) {
	if s == nil {
		return nil, fmt.Errorf("附件存储未配置")
	}

	return utils.InferTool(ListToolName,
		"列出当前会话中用户上传的全部附件。当你需要确认有哪些可用附件时使用。",
		func(ctx context.Context, _ ListInput) (ListOutput, error) {
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return ListOutput{}, err
			}

			rows, err := s.ListForConversation(ctx, p.UserID, p.ConversationID)
			if err != nil {
				return ListOutput{}, err
			}

			items := make([]AttachmentItem, 0, len(rows))
			for _, a := range rows {
				items = append(items, AttachmentItem{
					ID:       a.ID,
					Filename: a.Filename,
					Kind:     a.Kind,
					Size:     a.Size,
				})
			}

			msg := fmt.Sprintf("当前会话共有 %d 个附件。", len(items))
			if len(items) == 0 {
				msg = "当前会话没有附件。"
			}
			return ListOutput{Count: len(items), Items: items, Message: msg}, nil
		})
}

// Tools 返回全部附件工具。
func Tools(s *Store) ([]tool.BaseTool, error) {
	read, err := NewReadTool(s)
	if err != nil {
		return nil, err
	}
	list, err := NewListTool(s)
	if err != nil {
		return nil, err
	}
	return []tool.BaseTool{read, list}, nil
}

// ReadBytes 读取附件原始字节，供多模态构造使用。
func ReadBytes(s *Store, a *Attachment) ([]byte, error) {
	p, err := s.Path(a)
	if err != nil {
		return nil, err
	}
	return os.ReadFile(p)
}
