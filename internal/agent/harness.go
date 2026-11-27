// Package agent 的单轮运行上下文装配器（Harness）。
//
// 职责：
//   - 在 Service 校验会话归属并取得会话互斥锁之后、保存当前用户消息之前调用 Prepare()；
//   - 按“最新摘要检查点 + 检查点边界后的增量历史 + 本轮用户消息”顺序还原 Eino 原生消息序列；
//   - 为本轮会话创建物理工作区目录，并生成包含日期、工作区概览与本轮附件正文的 <turn_context>。
//
// 关键不变量：
//   - 必须在 Service.SaveUser 之前调用，否则历史查询会把本轮刚写入的用户消息重复拼入上下文；
//   - 历史消息仅附加轻量 <attachment_ref> 索引，绝不反复注入历史附件全文；
//   - 从检查点恢复的消息必须浅拷贝后再交给 Agent，防止运行期中间件修改缓存对象。
package agent

import (
	"cmp"
	"context"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/cloudwego/eino/schema"

	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
	"mentorly/internal/utils"
	logutil "mentorly/internal/utils/log"
)

// RunContext 封装单次 Agent.Run 所需的隔离身份与完整输入消息序列。
type RunContext struct {
	principal Principal
	Messages  []*schema.Message
}

// Harness 只持有只读依赖，不持有 Agent 实例或跨请求对话状态。
type Harness struct {
	workspaceDir  string
	conversations *conversations.Store
	attachments   *attachments.Store
}

// NewHarness 构造上下文装配器；workspaceDir 为空时回落至 DefaultWorkspaceDir。
func NewHarness(workspaceDir string, convs *conversations.Store, atts *attachments.Store) *Harness {
	return &Harness{
		workspaceDir:  cmp.Or(strings.TrimSpace(workspaceDir), DefaultWorkspaceDir),
		conversations: convs,
		attachments:   atts,
	}
}

// attachmentVirtualPath 是全包唯一的附件虚拟路径规则：以稳定附件 ID 定位原件，原始文件名仅作展示。
func attachmentVirtualPath(a *attachments.Attachment) string {
	return MountWorkspace + "/" + a.ID + a.Ext
}

// Prepare 装配单轮运行上下文，并返回该会话是否首次对话（供 Service 决定是否自动生成标题）。
func (h *Harness) Prepare(ctx context.Context, userID, conversationID, question string, current []*attachments.Attachment) (*RunContext, bool, error) {
	// 1. 先加载摘要检查点，再只查边界后的增量历史，避免把已被摘要覆盖的旧消息重复送入窗口。
	compaction, err := h.conversations.GetCompaction(ctx, conversationID)
	if err != nil {
		return nil, false, fmt.Errorf("加载压缩检查点失败: %w", err)
	}
	history, err := h.conversations.ListMessagesAfter(ctx, conversationID, compaction.UntilMessageID, 0)
	if err != nil {
		return nil, false, fmt.Errorf("加载历史消息失败: %w", err)
	}
	firstTurn := compaction.UntilMessageID == 0 && len(history) == 0

	// 2. 按 (userID, conversationID) 派生并创建隔离工作区，模型无法通过参数指定目录。
	workspace, err := utils.SafeJoin(h.workspaceDir, userID, conversationID)
	if err != nil {
		return nil, false, fmt.Errorf("解析工作目录失败: %w", err)
	}
	if err := os.MkdirAll(workspace, 0o755); err != nil {
		return nil, false, fmt.Errorf("创建工作目录失败: %w", err)
	}

	// 3. 为历史用户消息补齐附件索引标签，再还原为 Eino 原生消息序列（保留 ToolCall/ToolResult 关联）。
	history, err = attachHistoryRefs(ctx, h.attachments, userID, conversationID, history)
	if err != nil {
		return nil, false, err
	}

	msgs := make([]*schema.Message, 0, len(compaction.Messages)+len(history)+1)
	for _, m := range compaction.Messages {
		if m != nil && m.Role != schema.System {
			cp := *m
			msgs = append(msgs, &cp)
		}
	}
	msgs = append(msgs, conversations.ModelMessages(history)...)

	// 4. 追加本轮用户输入；主 System 提示词由 Agent Instruction 装配，不在此重复注入。
	userMsg := formatUserMessage(time.Now().Format("2006-01-02"), listWorkspaceFiles(workspace), question, current, h.attachments)
	msgs = append(msgs, userMsg)
	logutil.FromContext(ctx, nil).Info("[本轮上下文]", logutil.Content("内容", userMsg.Content))

	return &RunContext{
		principal: Principal{UserID: userID, ConversationID: conversationID, Workspace: workspace},
		Messages:  msgs,
	}, firstTurn, nil
}

// listWorkspaceFiles 列出工作区顶层最多 40 个非隐藏条目作为概览，不递归扫描也不预读正文。
func listWorkspaceFiles(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	out := make([]string, 0, min(len(entries), 40))
	for _, e := range entries {
		name := e.Name()
		if strings.HasPrefix(name, ".") {
			continue
		}
		if len(out) >= 40 {
			break
		}
		if e.IsDir() {
			name += "/"
		}
		out = append(out, name)
	}
	return out
}

// attachHistoryRefs 批量查询历史消息关联的附件并拼装 <attachment_ref> 索引标签，
// 同时按 userID + conversationID 过滤以防止跨会话引用泄露。
func attachHistoryRefs(ctx context.Context, s *attachments.Store, userID, conversationID string, history []conversations.Message) ([]conversations.Message, error) {
	var ids []string
	for _, m := range history {
		if m.Role == conversations.RoleUser {
			ids = append(ids, m.AttachmentIDs...)
		}
	}
	byID := make(map[string]*attachments.Attachment)
	if len(ids) > 0 && s != nil {
		rows, err := s.FindMany(ctx, userID, conversationID, ids)
		if err != nil {
			return nil, fmt.Errorf("加载历史附件失败: %w", err)
		}
		for _, a := range rows {
			byID[a.ID] = a
		}
	}

	out := append([]conversations.Message(nil), history...)
	for i := range out {
		if out[i].Role != conversations.RoleUser {
			continue
		}
		for _, id := range out[i].AttachmentIDs {
			if a := byID[id]; a != nil {
				out[i].Content += fmt.Sprintf("\n<attachment_ref id=%q name=%q path=%q status=%q />", id, a.Filename, attachmentVirtualPath(a), s.Status(a))
			} else {
				out[i].Content += fmt.Sprintf("\n<attachment_ref id=%q status=\"metadata_unavailable\" />", id)
			}
		}
	}
	return out, nil
}

// formatUserMessage 将日期、工作区概览、用户原问题与本轮附件正文组合为单条 User 消息。
func formatUserMessage(now string, wsFiles []string, question string, current []*attachments.Attachment, s *attachments.Store) *schema.Message {
	var ctxAttLines, docBlocks []string
	for _, a := range current {
		if a == nil {
			continue
		}
		vpath := attachmentVirtualPath(a)
		ctxAttLines = append(ctxAttLines, fmt.Sprintf("- %s（%s，%s）", vpath, a.Filename, a.Kind))

		status := "available"
		if s != nil {
			status = s.Status(a)
		} else if a.ExtractError != "" {
			status = "extraction_failed"
		}
		// 仅状态可用时注入提取正文；不可用时置空并提示模型改用 read_attachment 核实错误原因。
		body := a.Text
		if status != "available" {
			body = ""
		}
		block := fmt.Sprintf("<attachment id=%q name=%q path=%q status=%q>\n%s\n</attachment>", a.ID, a.Filename, vpath, status, body)
		if status != "available" {
			block += "\n（附件原件缺失、无法读取或提取失败，请用 read_attachment 确认状态，不能假设已读到正文。）"
		}
		docBlocks = append(docBlocks, block)
	}

	var sb strings.Builder
	sb.WriteString("<turn_context>\n")
	if now != "" {
		fmt.Fprintf(&sb, "今天是 %s。\n", now)
	}
	if len(wsFiles) > 0 {
		sb.WriteString("\n工作区已有内容（来自本次会话之前的轮次，可继续使用或修改）：\n")
		for _, f := range wsFiles {
			fmt.Fprintf(&sb, "- %s\n", f)
		}
	} else {
		sb.WriteString("\n工作区目前为空。\n")
	}
	if len(ctxAttLines) > 0 {
		sb.WriteString("\n本轮附件（原件已在 /workspace/ 下，可直接传给 Skill 脚本）：\n")
		sb.WriteString(strings.Join(ctxAttLines, "\n") + "\n")
	}
	sb.WriteString("</turn_context>\n\n")
	sb.WriteString(question)
	if len(docBlocks) > 0 {
		sb.WriteString("\n\n以下是用户随本条消息上传的文档内容：\n\n")
		sb.WriteString(strings.Join(docBlocks, "\n\n"))
	}
	return schema.UserMessage(sb.String())
}
