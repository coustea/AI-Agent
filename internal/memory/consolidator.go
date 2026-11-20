package memory

import (
	"context"
	_ "embed"
	"fmt"
	"strings"
	"time"

	"go.uber.org/zap"
)

//go:embed prompts/consolidate.md
var consolidatePrompt string

// ConsolidateResult 描述一次整合的结果，供 Harness 日志与测试断言。
type ConsolidateResult struct {
	// Triggered 是否实际触发了整合
	Triggered bool
	// Reason 触发原因，便于排障
	Reason string
	// Saved 记忆文档是否成功写入
	Saved bool
	// Cursor 推进后的记忆游标
	Cursor uint64
	// Doc 整合后的文档内容
	Doc string
}

// Consolidator 负责长期记忆的阈值判断与 Markdown 整合。
type Consolidator struct {
	model   ChatModel
	sess    SessionStore
	mem     MemoryStore
	counter Counter
	cfg     Config
	log     *zap.Logger
}

// NewConsolidator 构造整合器。
func NewConsolidator(model ChatModel, sess SessionStore, mem MemoryStore, cfg Config, log *zap.Logger) *Consolidator {
	if log == nil {
		log = zap.NewNop()
	}
	return &Consolidator{
		model:   model,
		sess:    sess,
		mem:     mem,
		counter: Counter{},
		cfg:     cfg,
		log:     log,
	}
}

// ShouldConsolidate 判断是否应触发整合。
//
// 传入的 pending 是「尚未提取的消息」（不含本轮当前消息）。
// pendingCompress 表示本次 Pre-Run 即将触发上下文压缩——此时必须先把旧消息
// 提炼进长期记忆，否则压缩丢弃原文后就再也提取不到了。
func (c *Consolidator) ShouldConsolidate(doc *MemoryDoc, pending []Message, pendingCompress bool) (bool, string) {
	if len(pending) == 0 {
		// 没有未提取消息也仍可能触发：remember 工具刚写过待整合条目。
		if doc != nil && HasPending(doc.Content) {
			return true, "pending_section"
		}
		return false, ""
	}

	// 待整合小节非空：remember 工具主动记录过内容，需要尽快并入正式章节。
	if doc != nil && HasPending(doc.Content) {
		return true, "pending_section"
	}

	if turns := CountTurns(pending); turns >= c.cfg.MemoryMinTurns {
		return true, fmt.Sprintf("turns=%d>=%d", turns, c.cfg.MemoryMinTurns)
	}

	if tokens := c.counter.EstimateMessages(pending); tokens >= c.cfg.MemoryMinTokens {
		return true, fmt.Sprintf("tokens=%d>=%d", tokens, c.cfg.MemoryMinTokens)
	}

	// 即将压缩且存在未提取旧消息：抢在原文被丢弃前提取。
	if pendingCompress {
		return true, "before_compress"
	}

	return false, ""
}

// MaybeConsolidate 按阈值决定并执行记忆整合。
// 失败只记 warn，不阻断对话——记忆是增强项，不是正确性前提。
func (c *Consolidator) MaybeConsolidate(ctx context.Context, sessionID string, currentMsgID uint64, pendingCompress bool) ConsolidateResult {
	sess, err := c.sess.GetSession(ctx, sessionID)
	if err != nil {
		c.log.Warn("读取会话失败，跳过记忆整合", zap.Error(err))
		return ConsolidateResult{}
	}

	all, err := c.sess.ListMessagesAfter(ctx, sessionID, sess.MemoryCursor)
	if err != nil {
		c.log.Warn("读取待提取消息失败，跳过记忆整合", zap.Error(err))
		return ConsolidateResult{}
	}

	// 排除本轮当前消息：它还没被回答，不属于「历史记忆」。
	pending := make([]Message, 0, len(all))
	for _, m := range all {
		if m.ID == currentMsgID {
			continue
		}
		pending = append(pending, m)
	}

	doc, err := c.mem.Get(ctx, sess.UserID)
	if err != nil {
		c.log.Warn("读取长期记忆失败，跳过整合", zap.Error(err))
		return ConsolidateResult{}
	}

	ok, reason := c.ShouldConsolidate(doc, pending, pendingCompress)
	if !ok {
		return ConsolidateResult{Reason: "below_threshold"}
	}

	// 无实际内容可整合（pending 为空且无待整合条目）时直接返回。
	if len(pending) == 0 && !HasPending(doc.Content) {
		return ConsolidateResult{Reason: "nothing_to_consolidate"}
	}

	newDoc, err := c.consolidate(ctx, doc.Content, pending)
	if err != nil {
		c.log.Warn("记忆整合失败，降级继续对话", zap.Error(err), zap.String("reason", reason))
		return ConsolidateResult{Triggered: true, Reason: reason}
	}

	// 后处理：去围栏、校验结构、清空待整合、限制长度。
	newDoc = StripCodeFence(newDoc)
	newDoc = ClearPending(newDoc)
	newDoc = TrimToMaxChars(newDoc, c.cfg.MemoryMaxChars)

	if !ValidateMemoryDoc(newDoc) {
		c.log.Warn("记忆整合结果结构不合法，保留原记忆", zap.String("preview", preview(newDoc, 200)))
		return ConsolidateResult{Triggered: true, Reason: reason, Doc: doc.Content}
	}

	saved, err := c.saveWithRetry(ctx, sess.UserID, newDoc, doc.Version)
	if err != nil {
		c.log.Warn("写入长期记忆失败", zap.Error(err))
		return ConsolidateResult{Triggered: true, Reason: reason}
	}
	if !saved {
		c.log.Warn("记忆写入乐观锁冲突且重试失败，保留原记忆")
		return ConsolidateResult{Triggered: true, Reason: reason, Doc: doc.Content}
	}

	// 游标推进到本次处理过的最后一条消息（不含本轮）。
	cursor := sess.MemoryCursor
	if len(pending) > 0 {
		cursor = pending[len(pending)-1].ID
	}
	if cursor > sess.MemoryCursor {
		if _, err := c.sess.AdvanceMemoryCursor(ctx, sessionID, cursor); err != nil {
			c.log.Warn("推进记忆游标失败", zap.Error(err))
		}
	}

	c.log.Info("长期记忆已整合",
		zap.String("reason", reason),
		zap.Uint64("cursor", cursor),
		zap.Int("pending_msgs", len(pending)),
	)

	return ConsolidateResult{
		Triggered: true,
		Reason:    reason,
		Saved:     true,
		Cursor:    cursor,
		Doc:       newDoc,
	}
}

// consolidate 调用 LLM 重写整份记忆文档。
func (c *Consolidator) consolidate(ctx context.Context, currentDoc string, pending []Message) (string, error) {
	var b strings.Builder

	b.WriteString("## 现有记忆档案\n\n")
	if strings.TrimSpace(currentDoc) == "" {
		b.WriteString("（尚无记忆）\n")
	} else {
		b.WriteString(currentDoc)
		b.WriteString("\n")
	}

	b.WriteString("\n## 待整合的新对话\n\n")
	for _, m := range pending {
		role := "学生"
		if m.IsAssistant() {
			role = "辅导员"
		}
		b.WriteString(role)
		b.WriteString("：")
		b.WriteString(strings.TrimSpace(m.Content))
		b.WriteString("\n\n")
	}

	b.WriteString("请输出整合后的完整记忆档案 Markdown。")

	return c.model.Complete(ctx, consolidatePrompt, b.String())
}

// saveWithRetry 乐观锁写入，冲突时基于最新版本重试一次。
//
// 重试的必要性：并发会话可能同时整合同一用户的记忆。一次冲突通常意味着
// 对方刚写入了一份更新的文档，重试时读到新版本再写即可，不必无限重试。
func (c *Consolidator) saveWithRetry(ctx context.Context, userID, content string, baseVersion int) (bool, error) {
	ok, err := c.mem.SaveWithVersion(ctx, userID, content, baseVersion)
	if err != nil {
		return false, err
	}
	if ok {
		return true, nil
	}

	latest, err := c.mem.Get(ctx, userID)
	if err != nil {
		return false, err
	}
	if latest.Version == baseVersion {
		// 版本没变却写失败，说明不是乐观锁冲突，重试也不会成功。
		return false, nil
	}

	return c.mem.SaveWithVersion(ctx, userID, content, latest.Version)
}

// preview 截取文本前缀用于日志。
func preview(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n]) + "..."
}

// nowDate 返回用于条目日期标注的短日期。
func nowDate() string {
	return time.Now().Format("2006-01-02")
}
