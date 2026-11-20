package attachments

import (
	"context"
	"encoding/base64"
	"fmt"
	"strings"

	"github.com/cloudwego/eino/schema"
)

// 单条消息内联图片的总大小上限。
//
// base64 会把体积放大 33%，而多数 OpenAI 兼容网关对请求体有上限（常见 20MB）。
// 超过时宁可只传文档文本并明确提示，也不要让整个请求被网关拒绝。
const maxInlineImageBytes = 8 << 20

// BuildUserMessage 构造携带附件的用户消息。
//
// 规则（与 Eino 消息协议一致）：
//   - 文本走 Content；
//   - 图片走 UserInputMultiContent 的 ImageURL 部件，base64 data URL 直传；
//   - 文档类附件不塞二进制，而是把已提取的文本以带标记的段落附加在文本中，
//     模型需要细节时再用 read_attachment 工具读取。
//
// 这样既用上了模型原生多模态，又不会把大量二进制塞进 Prompt。
func BuildUserMessage(ctx context.Context, s *Store, userID, question string, attachmentIDs []string) (*schema.Message, error) {
	if len(attachmentIDs) == 0 {
		return schema.UserMessage(question), nil
	}

	var (
		parts     []schema.MessageInputPart
		docBlocks []string
		notices   []string
		inlineSz  int
	)

	for _, id := range attachmentIDs {
		id = strings.TrimSpace(id)
		if id == "" {
			continue
		}

		a, err := s.GetForUser(ctx, id, userID)
		if err != nil {
			// 附件 ID 无效或不属于该用户：明确提示，不静默丢弃。
			notices = append(notices, fmt.Sprintf("（附件 %s 无法访问，可能已被删除或不属于当前用户）", id))
			continue
		}

		if a.NativeImage() {
			data, err := ReadBytes(s, a)
			if err != nil {
				notices = append(notices, fmt.Sprintf("（图片《%s》读取失败：%v）", a.Filename, err))
				continue
			}
			if inlineSz+len(data) > maxInlineImageBytes {
				notices = append(notices, fmt.Sprintf("（图片《%s》体积过大，未直接传入，请让学生压缩后重传）", a.Filename))
				continue
			}
			inlineSz += len(data)

			parts = append(parts, schema.MessageInputPart{
				Type: schema.ChatMessagePartTypeImageURL,
				Image: &schema.MessageInputImage{
					MessagePartCommon: schema.MessagePartCommon{
						Base64Data: &[]string{base64.StdEncoding.EncodeToString(data)}[0],
						MIMEType:   a.MIME,
					},
					Detail: schema.ImageURLDetailHigh,
				},
			})
			continue
		}

		// 文档类：用已提取文本构造带标记的段落。
		switch {
		case a.ExtractError != "":
			notices = append(notices, fmt.Sprintf("（附件《%s》无法解析：%s）", a.Filename, a.ExtractError))
		case strings.TrimSpace(a.Text) != "":
			block := fmt.Sprintf("<attachment id=%q name=%q>\n%s\n</attachment>",
				a.ID, a.Filename, a.Text)
			if a.Truncated {
				block += fmt.Sprintf("\n（以上内容已截断，完整内容请用 read_attachment 读取 id=%s）", a.ID)
			}
			docBlocks = append(docBlocks, block)
		default:
			notices = append(notices, fmt.Sprintf("（附件《%s》没有可提取的文本）", a.Filename))
		}
	}

	// 组装最终文本：用户问题 + 文档内容 + 提示
	var sb strings.Builder
	sb.WriteString(question)

	if len(docBlocks) > 0 {
		sb.WriteString("\n\n以下是用户随消息上传的文档内容：\n\n")
		sb.WriteString(strings.Join(docBlocks, "\n\n"))
	}
	if len(notices) > 0 {
		sb.WriteString("\n\n")
		sb.WriteString(strings.Join(notices, "\n"))
	}

	msg := &schema.Message{Role: schema.User, Content: sb.String()}

	// 图片部件要放在文本之前还是之后？
	// OpenAI 协议里顺序影响不大，但把文本放前面更符合「先说明再给图」的阅读顺序，
	// 因此这里文本作为第一个部件，图片紧随其后。
	if len(parts) > 0 {
		all := make([]schema.MessageInputPart, 0, len(parts)+1)
		all = append(all, schema.MessageInputPart{
			Type: schema.ChatMessagePartTypeText,
			Text: sb.String(),
		})
		all = append(all, parts...)
		msg.UserInputMultiContent = all
		// 有 MultiContent 时 Content 会被忽略，置空避免语义重复。
		msg.Content = ""
	}

	return msg, nil
}
