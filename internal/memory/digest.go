package memory

import (
	"context"
	_ "embed"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"go.uber.org/zap"

	"mentorly/internal/dialogue"
	"mentorly/internal/window"
)

//go:embed prompts/summarize.md
var summarizePrompt string

// CompressResult 描述一次上下文压缩的结果。
type CompressResult struct {
	// Triggered 是否触发压缩
	Triggered bool
	// Reason 触发原因
	Reason string
	// Compressed 是否成功写入
	Compressed bool
	// Summary 压缩后的摘要
	Summary string
	// Cursor 压缩后的 summary_cursor
	Cursor uint64
	// ContextTokens 压缩后重算的基线 token 数
	ContextTokens int
}

// Digest 是会话摘要的维护者：把旧对话滚动压缩成一段摘要。
//
// 与 Consolidator 的分工：Digest 维护「这条会话发生过什么」（会话内），
// Consolidator 维护「这位学生是谁」（跨会话）。
type Digest struct {
	model   ChatModel
	tx      Transcript
	counter window.Counter
	cfg     DigestConfig
	log     *zap.Logger
}

// DigestConfig 是压缩策略参数。
type DigestConfig struct {
	// TriggerTokens 触发压缩的 token 阈值
	TriggerTokens int
	// TriggerMessages 触发压缩的消息条数阈值
	TriggerMessages int
	// SourceMaxChars 单次送入压缩的原文最大字符数
	SourceMaxChars int
	// KeepRecentTurns 压缩时保留原文的最近轮数
	KeepRecentTurns int
	// Timeout 单次压缩调用的超时
	Timeout int
}

func (c DigestConfig) withDefaults() DigestConfig {
	if c.TriggerTokens <= 0 {
		c.TriggerTokens = 6000
	}
	if c.TriggerMessages <= 0 {
		c.TriggerMessages = 16
	}
	if c.SourceMaxChars <= 0 {
		c.SourceMaxChars = 8000
	}
	if c.KeepRecentTurns <= 0 {
		c.KeepRecentTurns = 2
	}
	return c
}

// NewDigest 构造压缩器。
func NewDigest(model ChatModel, tx Transcript, cfg DigestConfig, log *zap.Logger) *Digest {
	if log == nil {
		log = zap.NewNop()
	}
	return &Digest{
		model:   model,
		tx:      tx,
		counter: window.Counter{},
		cfg:     cfg.withDefaults(),
		log:     log,
	}
}

// Uncompressed 是「未压缩消息」视图，供 ShouldCompress 与窗口切分共用。
type Uncompressed struct {
	// Summary 当前摘要
	Summary string
	// ContextTokens 最近一轮真实上下文用量（0 表示尚无真实值）
	ContextTokens int
	// Messages 游标之后、且不含本轮当前消息的历史
	Messages []dialogue.Message
	// CurrentQuestion 本轮新输入
	CurrentQuestion string
	// SystemTokens 动态 System Prompt 的估算 token 数
	SystemTokens int
}

// EffectiveTokens 计算有效上下文 token 总量。
//
// 优先使用模型返回的真实基线（context_tokens）+ 本轮新增估算；
// 尚无真实值时退回本地估算（System Prompt + 摘要 + 历史）。
func (d *Digest) EffectiveTokens(u Uncompressed) int {
	historyTokens := d.counter.EstimateMessages(u.Messages)
	newInput := d.counter.Estimate(u.CurrentQuestion)

	if u.ContextTokens > 0 {
		return u.ContextTokens + newInput
	}

	return u.SystemTokens + d.counter.Estimate(u.Summary) + historyTokens + newInput
}

// ShouldCompress 判断是否触发压缩，返回原因。
func (d *Digest) ShouldCompress(u Uncompressed) (bool, string) {
	// 没有足够消息可压缩时不必触发，避免每次调用都白跑一次 LLM。
	if len(u.Messages) == 0 {
		return false, ""
	}

	if n := len(u.Messages); n >= d.cfg.TriggerMessages {
		return true, fmt.Sprintf("messages=%d>=%d", n, d.cfg.TriggerMessages)
	}

	if t := d.EffectiveTokens(u); t >= d.cfg.TriggerTokens {
		return true, fmt.Sprintf("tokens=%d>=%d", t, d.cfg.TriggerTokens)
	}

	return false, ""
}

// MaybeRun 按阈值决定并执行滚动压缩。
// 失败只记 warn：窗口重建时的 token 预算硬截断会兜底，对话仍可用。
func (d *Digest) MaybeRun(ctx context.Context, sessionID string, currentMsgID uint64, currentQuestion string, systemTokens int) CompressResult {
	sess, err := d.tx.Session(ctx, sessionID)
	if err != nil {
		d.log.Warn("读取会话失败，跳过压缩", zap.Error(err))
		return CompressResult{}
	}

	all, err := d.tx.MessagesAfter(ctx, sessionID, sess.SummaryCursor)
	if err != nil {
		d.log.Warn("读取未压缩消息失败，跳过压缩", zap.Error(err))
		return CompressResult{}
	}

	// 排除本轮当前消息与空的失败消息。
	msgs := make([]dialogue.Message, 0, len(all))
	for _, m := range all {
		if m.ID == currentMsgID || m.IsEmptyFailure() {
			continue
		}
		msgs = append(msgs, m)
	}

	u := Uncompressed{
		Summary:         sess.Summary,
		ContextTokens:   sess.ContextTokens,
		Messages:        msgs,
		CurrentQuestion: currentQuestion,
		SystemTokens:    systemTokens,
	}

	ok, reason := d.ShouldCompress(u)
	if !ok {
		// 保留判断依据，便于线上排查「为什么没压缩」。
		d.log.Debug("未达压缩阈值",
			zap.Int("messages", len(msgs)),
			zap.Int("trigger_messages", d.cfg.TriggerMessages),
			zap.Int("tokens", d.EffectiveTokens(u)),
			zap.Int("trigger_tokens", d.cfg.TriggerTokens),
		)
		return CompressResult{Reason: "below_threshold"}
	}

	win := window.SelectForCompression(msgs, d.cfg.KeepRecentTurns, d.cfg.SourceMaxChars)
	if len(win.ToCompress) == 0 || win.CutoffID == 0 {
		// 可压缩内容为空或单轮就超限：直接交给预算截断。
		return CompressResult{Triggered: true, Reason: reason + ";no_window"}
	}

	summary, err := d.compress(ctx, sess.Summary, win.ToCompress)
	if err != nil {
		d.log.Warn("上下文压缩失败，降级为预算截断", zap.Error(err), zap.String("reason", reason))
		return CompressResult{Triggered: true, Reason: reason}
	}

	summary = StripCodeFence(summary)
	if strings.TrimSpace(summary) == "" {
		d.log.Warn("压缩结果为空，保留原摘要")
		return CompressResult{Triggered: true, Reason: reason}
	}

	// 压缩后重算基线。
	//
	// 这里有个容易踩的坑：eino 会在真实 prompt 里注入工具 Schema 与技能清单，
	// 这部分固定开销（实测约 4.5-5k token）本地估算器完全看不到。
	// 若直接用「本地估算的 system + 摘要 + 保留原文」当新基线，
	// 算出来会远低于真实值（实测估算 3612 vs 真实 6803），
	// 于是下一轮立刻又超阈值、反复压缩却始终降不下来。
	//
	// 正确做法：从真实基线里剥离「可压缩部分」（旧摘要 + 被压缩的原文 + 保留原文），
	// 剩下的就是不可压缩的固定开销，再加上压缩后的新内容。
	fixedOverhead := 0
	if sess.ContextTokens > 0 {
		compressible := d.counter.Estimate(sess.Summary) +
			d.counter.EstimateMessages(win.ToCompress) +
			d.counter.EstimateMessages(win.Keep)
		fixedOverhead = sess.ContextTokens - compressible
		if fixedOverhead < 0 {
			// 估算偏大时不能得到负开销，退回纯估算路径。
			fixedOverhead = 0
		}
	}

	if fixedOverhead == 0 {
		// 尚无真实用量（首轮即触发压缩）：只能用估算值。
		fixedOverhead = systemTokens
	}

	newBaseline := fixedOverhead +
		d.counter.Estimate(summary) +
		d.counter.EstimateMessages(win.Keep) +
		d.counter.Estimate(currentQuestion)

	newBaselineResult := CompressResult{
		Triggered:     true,
		Reason:        reason,
		Compressed:    true,
		Summary:       summary,
		Cursor:        win.CutoffID,
		ContextTokens: newBaseline,
	}

	applied, err := d.tx.UpdateSummary(ctx, sessionID, summary, win.CutoffID, newBaseline)
	if err != nil {
		d.log.Warn("写回摘要失败", zap.Error(err))
		return CompressResult{Triggered: true, Reason: reason}
	}
	if !applied {
		// 条件更新未生效：说明游标已被推进到更靠后的位置（并发场景），
		// 本次结果已过期，丢弃即可。
		d.log.Warn("摘要游标已被并发推进，本次压缩结果丢弃", zap.Uint64("cutoff", win.CutoffID))
		return CompressResult{Triggered: true, Reason: reason}
	}

	d.log.Info("上下文已压缩",
		zap.String("reason", reason),
		zap.Uint64("cutoff", win.CutoffID),
		zap.Int("compressed_msgs", len(win.ToCompress)),
		zap.Int("kept_msgs", len(win.Keep)),
		zap.Int("baseline_tokens", newBaseline),
		zap.Int("fixed_overhead", fixedOverhead),
		zap.Int("prev_context_tokens", sess.ContextTokens),
	)

	return newBaselineResult
}

// compress 调用 LLM 生成滚动摘要。
func (d *Digest) compress(ctx context.Context, prevSummary string, msgs []dialogue.Message) (string, error) {
	var b strings.Builder

	b.WriteString("## 已有摘要\n\n")
	if strings.TrimSpace(prevSummary) == "" {
		b.WriteString("（无，本段是会话开头）\n")
	} else {
		b.WriteString(prevSummary)
		b.WriteString("\n")
	}

	b.WriteString("\n## 需要并入摘要的新对话\n\n")
	b.WriteString(window.Render(msgs, "学生", "辅导员"))
	b.WriteString("请输出合并后的完整摘要。")

	return d.model.Complete(ctx, summarizePrompt, b.String())
}

// PromptInput 是组装动态 System Prompt 的输入。
type PromptInput struct {
	// Base 静态底座 Prompt（agent/prompts/tutor.md）
	Base string
	// MemoryDoc 长期记忆文档
	MemoryDoc string
	// Summary 会话摘要
	Summary string
	// Files 工作区文件索引
	Files []string
}

// AssemblePrompt 按需拼装动态 System Prompt。
//
// 核心原则（Zero Empty Noise）：任何一段没有内容就不注入，
// 未压缩过的新会话、无记忆的新用户不会因此多付 token。
func AssemblePrompt(in PromptInput) string {
	var sb strings.Builder

	sb.WriteString(strings.TrimSpace(in.Base))

	sb.WriteString("\n\n## 当前日期\n\n")
	sb.WriteString(today())

	if strings.TrimSpace(in.MemoryDoc) != "" {
		sb.WriteString("\n\n## 关于这位学生\n\n")
		sb.WriteString(strings.TrimSpace(in.MemoryDoc))
	}

	if strings.TrimSpace(in.Summary) != "" {
		sb.WriteString("\n\n## 会话摘要\n\n")
		sb.WriteString(strings.TrimSpace(in.Summary))
	}

	if len(in.Files) > 0 {
		sb.WriteString("\n\n## 工作区文件\n\n")
		sb.WriteString("当前工作区已有以下文件，可直接用文件工具读取：\n")
		for _, f := range in.Files {
			sb.WriteString("- /workspace/")
			sb.WriteString(f)
			sb.WriteString("\n")
		}
	}

	return sb.String()
}

// ListWorkspaceFiles 返回工作区内的文件索引（相对路径），最多列出 30 个。
// 工作区不存在或为空时返回 nil，调用方据此跳过注入。
func ListWorkspaceFiles(root, userID, sessionID string) []string {
	if strings.TrimSpace(root) == "" {
		return nil
	}

	dir := filepath.Join(root, userID, sessionID)
	entries, err := os.ReadDir(dir)
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

// today 返回记忆条目与提示词使用的短日期。
func today() string {
	return time.Now().Format("2006-01-02")
}
