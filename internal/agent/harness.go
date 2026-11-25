package agent

import (
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

// 单轮上下文装配流水线（最终送入 Eino Runner.Run 的消息结构）：
//   1. [System Prompt]          由 Eino deep.New 启动期装配，不存数据库
//   2. [Compacted Summary...]   数据库最近一次 summarization 检查点（剔除 system）
//   3. [Full History...]        检查点之后的完整历史（历史用户消息附加 <attachment_ref>；旧工具清理由官方 reduction 中间件统一负责）
//   4. [Current User Message]   <turn_context>（日期/工作区文件/本轮附件路径）+ 问题 + 本轮附件正文

// RunContext 包含一次 Agent 运行所需的隔离身份与消息序列，不持有数据库连接。
type RunContext struct {
	principal *runPrincipal
	Messages  []*schema.Message
}

// Harness 负责单轮运行准备：读取历史、准备隔离工作区、装配本轮上下文消息。
// 按分层约束独立于 Agent 之外，确保 Agent 不依赖数据库且在 Service.SaveUser 之前读取历史。
type Harness struct {
	attachments   *attachments.Store
	conversations *conversations.Store
	cfg           Config
}

// HarnessDeps 是构造 Harness 所需的依赖与配置。
type HarnessDeps struct {
	Attachments   *attachments.Store
	Conversations *conversations.Store
	Config        Config
}

// NewHarness 构造单轮上下文准备器。
func NewHarness(d HarnessDeps) *Harness {
	return &Harness{attachments: d.Attachments, conversations: d.Conversations, cfg: d.Config}
}

// attachmentVirtualPath 返回附件在 Agent 虚拟文件系统中的路径（/workspace/<id><ext>）。
func attachmentVirtualPath(a *attachments.Attachment) string {
	return MountWorkspace + "/" + a.ID + a.Ext
}

// Prepare 按 4 步准备本轮运行上下文并返回是否为首轮对话（用于决定是否自动生成会话标题）。
func (h *Harness) Prepare(ctx context.Context, userID, conversationID, question string, current []*attachments.Attachment) (*RunContext, bool, error) {
	// 1. 读取压缩检查点与检查点之后的历史消息。
	compaction, err := h.conversations.GetCompaction(ctx, conversationID)
	if err != nil {
		return nil, false, fmt.Errorf("加载压缩检查点失败: %w", err)
	}
	history, err := h.conversations.ListMessagesAfter(ctx, conversationID, compaction.UntilMessageID, 0)
	if err != nil {
		return nil, false, fmt.Errorf("加载历史消息失败: %w", err)
	}
	firstTurn := compaction.UntilMessageID == 0 && len(history) == 0

	// 2. 准备当前会话的隔离工作区。
	wsRoot := h.cfg.WorkspaceDir
	if strings.TrimSpace(wsRoot) == "" {
		wsRoot = DefaultWorkspaceDir
	}
	workspace, err := utils.SafeJoin(wsRoot, userID, conversationID)
	if err != nil {
		return nil, false, fmt.Errorf("解析工作目录失败: %w", err)
	}
	if err := os.MkdirAll(workspace, 0o755); err != nil {
		return nil, false, fmt.Errorf("创建工作目录失败: %w", err)
	}

	// 3. 装配历史上下文：为检查点之后的完整历史补齐附件引用标记（旧工具清理由官方 reduction 中间件执行）。
	withRefs, err := attachHistoryRefs(ctx, h.attachments, userID, conversationID, history)
	if err != nil {
		return nil, false, err
	}

	// 4. 拼接完整消息序列：[压缩摘要] + [历史消息] + [本轮用户消息]。
	// 浅拷贝检查点消息并过滤 schema.System，避免污染缓存对象或重复注入系统提示词。
	msgs := make([]*schema.Message, 0, len(compaction.Messages)+len(withRefs)+1)
	for _, m := range compaction.Messages {
		if m != nil && m.Role != schema.System {
			cp := *m
			msgs = append(msgs, &cp)
		}
	}
	msgs = append(msgs, conversations.ModelMessages(withRefs)...)

	userMsg := formatUserMessage(time.Now().Format("2006-01-02"), listWorkspaceFiles(workspace), question, current, h.attachments)
	msgs = append(msgs, userMsg)
	logutil.FromContext(ctx, nil).Info("[本轮上下文]", logutil.Content("内容", userMsg.Content))

	return &RunContext{
		principal: &runPrincipal{UserID: userID, ConversationID: conversationID, Workspace: workspace},
		Messages:  msgs,
	}, firstTurn, nil
}

// listWorkspaceFiles 列出工作区顶层可见条目供 <turn_context> 展示；跳过隐藏目录（如 .tmp/.offload），最多 40 项。
func listWorkspaceFiles(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	out := make([]string, 0, min(len(entries), 40))
	for _, e := range entries {
		if strings.HasPrefix(e.Name(), ".") {
			continue
		}
		if len(out) >= 40 {
			break
		}
		if e.IsDir() {
			out = append(out, e.Name()+"/")
		} else {
			out = append(out, e.Name())
		}
	}
	return out
}

// attachHistoryRefs 在历史用户消息末尾附加 <attachment_ref> 索引（不复制正文，需要时由 read_attachment 按需读取）。
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

	// 拷贝切片，避免直接修改调用方传入的 history。
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

// formatUserMessage 一次遍历 current，拼出 <turn_context> + 用户问题 + 本轮附件正文块。
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
	return &schema.Message{Role: schema.User, Content: sb.String()}
}
