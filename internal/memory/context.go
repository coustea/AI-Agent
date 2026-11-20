package memory

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"go.uber.org/zap"
)

// BuiltContext 是 Pre-Run 的产物：已组装好的动态 System Prompt 与干净的消息切片。
type BuiltContext struct {
	// Instruction 动态拼装的 System Prompt
	Instruction string
	// Messages 预算截断后的历史消息（不含本轮当前问题）
	Messages []Message
	// Summary 本轮使用的会话摘要
	Summary string
	// MemoryDoc 本轮使用的长期记忆
	MemoryDoc string
	// HistoryTokens 历史消息的估算 token 数
	HistoryTokens int
	// SystemTokens System Prompt 的估算 token 数
	SystemTokens int
	// WorkspaceFiles 工作区文件索引（空表示无文件）
	WorkspaceFiles []string
}

// ContextRequest 是 Build 的入参。
type ContextRequest struct {
	UserID    string
	SessionID string
	// CurrentMsgID 本轮 user 消息 id，构建历史时需排除
	CurrentMsgID uint64
	// CurrentQuestion 本轮用户问题
	CurrentQuestion string
	// BasePrompt 静态底座 System Prompt（agent/prompts/tutor.md 的内容）
	BasePrompt string
}

// Builder 是调用 Agent 前的上下文准备管线：
//
//  1. 记忆提取（Consolidator）
//  2. 上下文压缩（Summarizer）
//  3. 用最新摘要/记忆/历史重建上下文并做预算截断
//
// 顺序不可交换：先提取记忆，才能在压缩丢弃原文前保住长期信息；
// 先压缩，第 3 步读到的才是压缩后的最小历史。
type Builder struct {
	sess    SessionStore
	mem     MemoryStore
	consol  *Consolidator
	summary *Summarizer
	counter Counter
	cfg     Config
	log     *zap.Logger
}

// NewBuilder 构造上下文构建器。
func NewBuilder(model ChatModel, sess SessionStore, mem MemoryStore, cfg Config, log *zap.Logger) *Builder {
	if log == nil {
		log = zap.NewNop()
	}
	cfg = cfg.withDefaults()

	return &Builder{
		sess:    sess,
		mem:     mem,
		consol:  NewConsolidator(model, sess, mem, cfg, log),
		summary: NewSummarizer(model, sess, cfg, log),
		counter: Counter{},
		cfg:     cfg,
		log:     log,
	}
}

// Build 严格执行三步管线，返回本轮可用的上下文。
func (b *Builder) Build(ctx context.Context, req ContextRequest) (*BuiltContext, error) {
	if strings.TrimSpace(req.BasePrompt) == "" {
		return nil, fmt.Errorf("base prompt 不能为空")
	}

	// 先估算一次动态 System Prompt 的规模，供压缩阈值判断使用。
	// 此处的记忆/摘要还是「压缩前」的版本，只用于判断是否超阈值，
	// 真正的 Instruction 在第 3 步用最新数据重建。
	preSystem := b.assemblePrompt(req.BasePrompt, "", "", nil)
	systemTokens := b.counter.Estimate(preSystem)

	// ---------- 第 1 步：长期记忆提取 ----------
	// 先探一下本次是否会压缩，让整合器能在原文被丢弃前抢跑。
	willCompress := b.peekCompress(ctx, req)
	b.consol.MaybeConsolidate(ctx, req.SessionID, req.CurrentMsgID, willCompress)

	// ---------- 第 2 步：上下文滚动压缩 ----------
	b.summary.MaybeCompress(ctx, req.SessionID, req.CurrentMsgID, req.CurrentQuestion, systemTokens)

	// ---------- 第 3 步：用最新状态重建上下文 ----------
	sess, err := b.sess.GetSession(ctx, req.SessionID)
	if err != nil {
		return nil, fmt.Errorf("读取会话失败: %w", err)
	}

	doc, err := b.mem.Get(ctx, sess.UserID)
	if err != nil {
		return nil, fmt.Errorf("读取长期记忆失败: %w", err)
	}
	// 空小节会白占 token，注入前先剔除。
	memoryDoc := PruneEmptySections(doc.Content)

	// 压缩游标之后的消息即为剩余历史。
	history, err := b.sess.ListMessagesAfter(ctx, req.SessionID, sess.SummaryCursor)
	if err != nil {
		return nil, fmt.Errorf("读取历史消息失败: %w", err)
	}

	// 排除本轮当前消息与空失败消息——当前问题会单独追加。
	candidates := make([]Message, 0, len(history))
	for _, m := range history {
		if m.ID == req.CurrentMsgID {
			continue
		}
		if m.Status == "failed" && strings.TrimSpace(m.Content) == "" {
			continue
		}
		candidates = append(candidates, m)
	}

	files := b.listWorkspaceFiles(ctx, sess.UserID, sess.ID)
	instruction := b.assemblePrompt(req.BasePrompt, memoryDoc, sess.Summary, files)
	systemTokens = b.counter.Estimate(instruction)

	// 历史预算 = 总预算 - System Prompt - 本轮问题。
	budget := b.cfg.HistoryBudgetTokens - systemTokens - b.counter.Estimate(req.CurrentQuestion)
	kept, keptTokens := fitHistory(candidates, budget, b.cfg.HistoryMaxMessages, b.counter)

	return &BuiltContext{
		Instruction:    instruction,
		Messages:       kept,
		Summary:        sess.Summary,
		MemoryDoc:      memoryDoc,
		HistoryTokens:  keptTokens,
		SystemTokens:   systemTokens,
		WorkspaceFiles: files,
	}, nil
}

// peekCompress 用压缩前状态判断本次 Pre-Run 是否会触发压缩。
func (b *Builder) peekCompress(ctx context.Context, req ContextRequest) bool {
	sess, err := b.sess.GetSession(ctx, req.SessionID)
	if err != nil {
		return false
	}
	msgs, err := b.sess.ListMessagesAfter(ctx, req.SessionID, sess.SummaryCursor)
	if err != nil {
		return false
	}

	filtered := make([]Message, 0, len(msgs))
	for _, m := range msgs {
		if m.ID == req.CurrentMsgID {
			continue
		}
		filtered = append(filtered, m)
	}

	u := Uncompressed{
		Summary:         sess.Summary,
		ContextTokens:   sess.ContextTokens,
		Messages:        filtered,
		CurrentQuestion: req.CurrentQuestion,
	}
	ok, _ := b.summary.ShouldCompress(u)
	return ok
}

// assemblePrompt 按需拼装动态 System Prompt。
//
// 核心原则（Zero Empty Noise）：任何一段没有内容就不注入，
// 未压缩过的新会话、无记忆的新用户不会因此多付 token。
func (b *Builder) assemblePrompt(base, memoryDoc, summary string, files []string) string {
	var sb strings.Builder

	sb.WriteString(strings.TrimSpace(base))

	// [当前日期] 始终注入
	sb.WriteString("\n\n## 当前日期\n\n")
	sb.WriteString(time.Now().Format("2006-01-02"))

	if strings.TrimSpace(memoryDoc) != "" {
		sb.WriteString("\n\n## 关于这位学生\n\n")
		sb.WriteString(strings.TrimSpace(memoryDoc))
	}

	if strings.TrimSpace(summary) != "" {
		sb.WriteString("\n\n## 会话摘要\n\n")
		sb.WriteString(strings.TrimSpace(summary))
	}

	if len(files) > 0 {
		sb.WriteString("\n\n## 工作区文件\n\n")
		sb.WriteString("当前工作区已有以下文件，可直接用文件工具读取：")
		sb.WriteString("\n")
		for _, f := range files {
			sb.WriteString("- /workspace/")
			sb.WriteString(f)
			sb.WriteString("\n")
		}
	}

	return sb.String()
}

// listWorkspaceFiles 返回工作区内的文件索引（相对路径），最多列出 30 个。
// 工作区不存在或为空时返回 nil，调用方据此跳过注入。
func (b *Builder) listWorkspaceFiles(_ context.Context, userID, sessionID string) []string {
	if strings.TrimSpace(b.cfg.WorkspaceRoot) == "" {
		return nil
	}

	root := filepath.Join(b.cfg.WorkspaceRoot, userID, sessionID)
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil
	}

	files := make([]string, 0, len(entries))
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		files = append(files, e.Name())
		if len(files) >= 30 {
			break
		}
	}
	if len(files) == 0 {
		return nil
	}
	sort.Strings(files)
	return files
}

// fitHistory 从最新消息往前按预算保留历史，并做对话结构修正。
//
// 规则（与计划一致）：
//   - 从最新往前累加，超过预算即停止；
//   - 跳过 status=failed 的空消息；
//   - 结果必须以 user 开头（丢弃开头的 assistant 孤儿消息）；
//   - user / assistant 必须交替，丢弃连续的同类消息（保留更早的那条，
//     因为连续的 assistant 中间被丢掉的往往是工具调用轮次）。
//
// 返回保留下来的消息与它们的估算 token 总量。
func fitHistory(msgs []Message, budgetTokens, maxMessages int, counter Counter) ([]Message, int) {
	if len(msgs) == 0 {
		return nil, 0
	}
	if maxMessages <= 0 {
		maxMessages = 40
	}

	// 1. 从后往前按预算（与条数上限）收集。
	var picked []Message
	tokens := 0

	for i := len(msgs) - 1; i >= 0; i-- {
		m := msgs[i]

		// 跳过空失败消息：它们对模型没有信息量，还会破坏交替结构。
		if m.Status == "failed" && strings.TrimSpace(m.Content) == "" {
			continue
		}

		mt := counter.Estimate(m.Content) + 4
		if len(picked) >= maxMessages {
			break
		}

		// 预算不足时仍要保留至少一条：没有历史上下文，模型会完全失去对话感。
		// 这里对第一条无条件收录，之后才严格按预算停止。
		if tokens+mt > budgetTokens && len(picked) > 0 {
			break
		}

		tokens += mt
		picked = append(picked, m)
	}

	// 2. 反转回时间升序。
	for i, j := 0, len(picked)-1; i < j; i, j = i+1, j-1 {
		picked[i], picked[j] = picked[j], picked[i]
	}

	// 3. 若收集到的片段全是 assistant（预算只够最后一条回答），
	// 继续往前补一条 user，否则 normalizeAlternation 会把它整段丢弃，
	// 结果就是「有预算但零上下文」——这比稍微超预算更糟。
	hasUser := false
	for _, m := range picked {
		if m.IsUser() {
			hasUser = true
			break
		}
	}
	if !hasUser && len(picked) > 0 {
		firstID := picked[0].ID
		for i := len(msgs) - 1; i >= 0; i-- {
			m := msgs[i]
			if m.ID >= firstID {
				continue
			}
			if m.Status == "failed" && strings.TrimSpace(m.Content) == "" {
				continue
			}
			if m.IsUser() {
				picked = append([]Message{m}, picked...)
				tokens += counter.Estimate(m.Content) + 4
				break
			}
		}
	}

	// 4. 修正结构：以 user 开头，user/assistant 交替。
	return normalizeAlternation(picked, counter)
}

// normalizeAlternation 让消息切片以 user 开头且 user/assistant 交替。
func normalizeAlternation(msgs []Message, counter Counter) ([]Message, int) {
	if len(msgs) == 0 {
		return nil, 0
	}

	// 丢弃开头连续的 assistant 消息（缺少对应问题的孤儿回答）。
	start := 0
	for start < len(msgs) && !msgs[start].IsUser() {
		start++
	}
	if start == len(msgs) {
		// 全是 assistant：无法构成合法对话，返回空历史。
		return nil, 0
	}

	out := make([]Message, 0, len(msgs)-start)
	var lastRole string

	for _, m := range msgs[start:] {
		role := m.Role

		// 同类消息连发：保留先出现的那条，跳过后续的。
		if role == lastRole {
			continue
		}

		out = append(out, m)
		lastRole = role
	}

	// 若以 assistant 结尾，说明最后一条回答没有后续问题，
	// 这是正常历史（下一轮的问题会追加在它后面），无需处理。

	tokens := counter.EstimateMessages(out)
	return out, tokens
}
