package chat

import (
	"context"
	_ "embed"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"go.uber.org/zap"
)

// ---------- 上下文滚动压缩 ----------

//go:embed prompts/summarize.md
var summarizePrompt string

// CompressResult 描述一次压缩的结果，供日志与测试断言。
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

// compressor 维护会话语义摘要：把旧对话滚动压缩成一段摘要。
//
// 与「一轮对话」的分工：compressor 只回答「什么时候压、压什么、新基线是多少」，
// 真正的 LLM 调用与写库由 service 驱动。这样策略可以脱离 DB 与网络单测。
type compressor struct {
	runner  *AgentRunner
	store   *Store
	counter Counter
	cfg     Config
	log     *zap.Logger
}

// uncompressed 是「未压缩消息」视图，供阈值判断与窗口切分共用。
type uncompressed struct {
	// Summary 当前摘要
	Summary string
	// ContextTokens 最近一轮真实上下文用量（0 表示尚无真实值）
	ContextTokens int
	// Messages 游标之后、且不含本轮当前消息的历史
	Messages []Message
	// CurrentQuestion 本轮新输入
	CurrentQuestion string
	// SystemTokens 动态 System Prompt 的估算 token 数
	SystemTokens int
}

// shouldCompress 判断是否触发压缩，返回原因。
//
// 纯函数：只读入参，不碰 store、不调模型。
func shouldCompress(u uncompressed, cfg Config, c Counter) (bool, string) {
	// 没有足够消息可压缩时不必触发，避免每次调用都白跑一次 LLM。
	if len(u.Messages) == 0 {
		return false, ""
	}

	if n := len(u.Messages); n >= cfg.CompressTriggerMessages {
		return true, fmt.Sprintf("messages=%d>=%d", n, cfg.CompressTriggerMessages)
	}

	if t := effectiveTokens(u, c); t >= cfg.CompressTriggerTokens {
		return true, fmt.Sprintf("tokens=%d>=%d", t, cfg.CompressTriggerTokens)
	}

	return false, ""
}

// effectiveTokens 计算有效上下文 token 总量。
//
// 优先使用模型返回的真实基线（context_tokens）+ 本轮新增估算；
// 尚无真实值时退回本地估算（System Prompt + 摘要 + 历史）。
func effectiveTokens(u uncompressed, c Counter) int {
	newInput := c.Estimate(u.CurrentQuestion)

	if u.ContextTokens > 0 {
		return u.ContextTokens + newInput
	}

	return u.SystemTokens + c.Estimate(u.Summary) + c.EstimateMessages(u.Messages) + newInput
}

// newBaseline 计算压缩后的新上下文基线。
//
// 这里有个容易踩的坑：eino 会在真实 prompt 里注入工具 Schema 与技能清单，
// 这部分固定开销（实测约 4.5-5k token）本地估算器完全看不到。
// 若直接用「本地估算的 system + 摘要 + 保留原文」当新基线，
// 算出来会远低于真实值（实测估算 3612 vs 真实 6803），
// 于是下一轮立刻又超阈值、反复压缩却始终降不下来。
//
// 正确做法：从真实基线里剥离「可压缩部分」（旧摘要 + 被压缩的原文 + 保留原文），
// 剩下的就是不可压缩的固定开销，再加上压缩后的新内容。
func newBaseline(
	prevContextTokens int,
	prevSummary string,
	compressed, kept []Message,
	newSummary, question string,
	systemTokens int,
	c Counter,
) (baseline, fixedOverhead int) {
	if prevContextTokens > 0 {
		compressible := c.Estimate(prevSummary) +
			c.EstimateMessages(compressed) +
			c.EstimateMessages(kept)
		fixedOverhead = prevContextTokens - compressible
		if fixedOverhead < 0 {
			// 估算偏大时不能得到负开销，退回纯估算路径。
			fixedOverhead = 0
		}
	}

	if fixedOverhead == 0 {
		// 尚无真实用量（首轮即触发压缩）：只能用估算值。
		fixedOverhead = systemTokens
	}

	baseline = fixedOverhead +
		c.Estimate(newSummary) +
		c.EstimateMessages(kept) +
		c.Estimate(question)

	return baseline, fixedOverhead
}

// MaybeRun 按阈值决定并执行滚动压缩。
// 失败只记 warn：窗口重建时的 token 预算硬截断会兜底，对话仍可用。
func (s *Service) MaybeRun(ctx context.Context, sess *Session, history []Message, question string, systemTokens int) CompressResult {
	if s == nil || s.agent == nil || s.store == nil {
		return CompressResult{}
	}

	u := uncompressed{
		Summary:         sess.Summary,
		ContextTokens:   sess.ContextTokens,
		Messages:        history,
		CurrentQuestion: question,
		SystemTokens:    systemTokens,
	}

	ok, reason := shouldCompress(u, s.cfg, s.counter)
	if !ok {
		// 保留判断依据，便于线上排查「为什么没压缩」。
		s.log.Debug("未达压缩阈值",
			zap.Int("messages", len(history)),
			zap.Int("trigger_messages", s.cfg.CompressTriggerMessages),
			zap.Int("tokens", effectiveTokens(u, s.counter)),
			zap.Int("trigger_tokens", s.cfg.CompressTriggerTokens),
		)
		return CompressResult{Reason: "below_threshold"}
	}

	win := SelectForCompression(history, s.cfg.KeepRecentTurns, s.cfg.CompressSourceMaxChars)
	if len(win.ToCompress) == 0 || win.CutoffID == 0 {
		// 可压缩内容为空或单轮就超限：直接交给预算截断。
		return CompressResult{Triggered: true, Reason: reason + ";no_window"}
	}

	summary, err := s.compress(ctx, sess.Summary, win.ToCompress)
	if err != nil {
		s.log.Warn("上下文压缩失败，降级为预算截断", zap.Error(err), zap.String("reason", reason))
		return CompressResult{Triggered: true, Reason: reason}
	}

	summary = StripCodeFence(summary)
	if strings.TrimSpace(summary) == "" {
		s.log.Warn("压缩结果为空，保留原摘要")
		return CompressResult{Triggered: true, Reason: reason}
	}

	baseline, fixedOverhead := newBaseline(
		sess.ContextTokens, sess.Summary,
		win.ToCompress, win.Keep,
		summary, question,
		systemTokens, s.counter,
	)

	applied, err := s.store.UpdateSummary(ctx, sess.ID, summary, win.CutoffID, baseline)
	if err != nil {
		s.log.Warn("写回摘要失败", zap.Error(err))
		return CompressResult{Triggered: true, Reason: reason}
	}
	if !applied {
		// 条件更新未生效：说明游标已被推进到更靠后的位置（并发场景），
		// 本次结果已过期，丢弃即可。
		s.log.Warn("摘要游标已被并发推进，本次压缩结果丢弃", zap.Uint64("cutoff", win.CutoffID))
		return CompressResult{Triggered: true, Reason: reason}
	}

	// 回写领域对象，供调用方读取最新状态。
	sess.Summary = summary
	sess.SummaryCursor = win.CutoffID
	sess.ContextTokens = baseline

	s.log.Info("上下文已压缩",
		zap.String("reason", reason),
		zap.Uint64("cutoff", win.CutoffID),
		zap.Int("compressed_msgs", len(win.ToCompress)),
		zap.Int("kept_msgs", len(win.Keep)),
		zap.Int("baseline_tokens", baseline),
		zap.Int("fixed_overhead", fixedOverhead),
		zap.Int("prev_context_tokens", sess.ContextTokens),
	)

	return CompressResult{
		Triggered:     true,
		Reason:        reason,
		Compressed:    true,
		Summary:       summary,
		Cursor:        win.CutoffID,
		ContextTokens: baseline,
	}
}

// compress 调用 LLM 生成滚动摘要。
func (s *Service) compress(ctx context.Context, prevSummary string, msgs []Message) (string, error) {
	var b strings.Builder

	b.WriteString("## 已有摘要\n\n")
	if strings.TrimSpace(prevSummary) == "" {
		b.WriteString("（无，本段是会话开头）\n")
	} else {
		b.WriteString(prevSummary)
		b.WriteString("\n")
	}

	b.WriteString("\n## 需要并入摘要的新对话\n\n")
	b.WriteString(Render(msgs, "学生", "辅导员"))
	b.WriteString("请输出合并后的完整摘要。")

	return s.agent.Complete(ctx, summarizePrompt, b.String())
}

// StripCodeFence 去掉模型偶尔包裹的 Markdown 代码围栏。
func StripCodeFence(s string) string {
	t := strings.TrimSpace(s)
	if !strings.HasPrefix(t, "```") {
		return t
	}

	// 去掉起始行（``` 或 ```markdown）
	if i := strings.Index(t, "\n"); i >= 0 {
		t = t[i+1:]
	} else {
		return ""
	}
	// 去掉结束围栏
	if i := strings.LastIndex(t, "```"); i >= 0 {
		t = t[:i]
	}
	return strings.TrimSpace(t)
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
