package memory

import (
	"context"
	_ "embed"
	"fmt"
	"strings"

	"go.uber.org/zap"
)

//go:embed prompts/summarize.md
var summarizePrompt string

// CompressResult 描述一次压缩的结果。
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

// Summarizer 负责滚动上下文压缩。
type Summarizer struct {
	model   ChatModel
	sess    SessionStore
	counter Counter
	cfg     Config
	log     *zap.Logger
}

// NewSummarizer 构造压缩器。
func NewSummarizer(model ChatModel, sess SessionStore, cfg Config, log *zap.Logger) *Summarizer {
	if log == nil {
		log = zap.NewNop()
	}
	return &Summarizer{
		model:   model,
		sess:    sess,
		counter: Counter{},
		cfg:     cfg,
		log:     log,
	}
}

// Uncompressed 是「未压缩消息」视图，供 ShouldCompress 与 selectWindow 共用。
type Uncompressed struct {
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

// EffectiveTokens 计算有效上下文 token 总量。
//
// 优先使用模型返回的真实基线（context_tokens）+ 本轮新增估算；
// 尚无真实值时退回本地估算（System Prompt + 摘要 + 历史）。
func (s *Summarizer) EffectiveTokens(u Uncompressed) int {
	historyTokens := s.counter.EstimateMessages(u.Messages)
	newInput := s.counter.Estimate(u.CurrentQuestion)

	if u.ContextTokens > 0 {
		return u.ContextTokens + newInput
	}

	return u.SystemTokens + s.counter.Estimate(u.Summary) + historyTokens + newInput
}

// ShouldCompress 判断是否触发压缩，返回原因。
func (s *Summarizer) ShouldCompress(u Uncompressed) (bool, string) {
	// 没有足够消息可压缩时不必触发，避免每次调用都白跑一次 LLM。
	if len(u.Messages) == 0 {
		return false, ""
	}

	if n := len(u.Messages); n >= s.cfg.CompressTriggerMessages {
		return true, fmt.Sprintf("messages=%d>=%d", n, s.cfg.CompressTriggerMessages)
	}

	if t := s.EffectiveTokens(u); t >= s.cfg.CompressTriggerTokens {
		return true, fmt.Sprintf("tokens=%d>=%d", t, s.cfg.CompressTriggerTokens)
	}

	return false, ""
}

// Window 是 selectWindow 的结果。
type Window struct {
	// ToCompress 需要送入压缩的旧消息（整轮为界，时间升序）
	ToCompress []Message
	// Keep 保留原文的最近消息
	Keep []Message
	// CutoffID 送入压缩的最后一条消息 id，用作新的 summary_cursor；0 表示不压缩
	CutoffID uint64
}

// selectWindow 纯函数：切分「送去压缩」与「保留原文」的边界。
//
// 规则：
//  1. 保留最近 keepRecentTurns 轮原文（一轮指从一条 user 消息到其后的 assistant 回复）；
//  2. 边界之前、且总字符数不超过 maxChars 的消息送去压缩；
//  3. 按**整轮**截断：一旦某一轮放不下，就停止，不再尝试更早的轮次，
//     避免把同一轮拆成「压缩一半、保留一半」导致语义断裂。
//
// 调用方需保证 messages 已排除本轮当前消息，且按 id 升序。
func selectWindow(messages []Message, keepRecentTurns, maxChars int) Window {
	if len(messages) == 0 {
		return Window{}
	}
	if keepRecentTurns < 0 {
		keepRecentTurns = 0
	}

	// 1. 按「轮」分组：每条 user 消息开启一轮，后续 assistant 消息归入该轮。
	turns := groupTurns(messages)

	// 2. 从后往前保留 keepRecentTurns 轮。
	keepFrom := len(turns) - keepRecentTurns
	if keepFrom < 0 {
		keepFrom = 0
	}

	candidates := turns[:keepFrom]
	if len(candidates) == 0 {
		// 全部轮次都要保留原文，无可压缩内容。
		return Window{Keep: flatten(turns)}
	}

	// 3. 从最新一轮往前累加，超过 maxChars 即停止（按整轮截断）。
	var (
		picked   []Message
		chars    int
		cutoffID uint64
	)

	for i := len(candidates) - 1; i >= 0; i-- {
		turn := candidates[i]

		turnChars := turnCharCount(turn)
		if chars+turnChars > maxChars {
			break
		}
		chars += turnChars

		// 循环从最新一轮往前扫描，因此第一次纳入的轮次就是压缩区间的末尾。
		// cutoff 只在第一次赋值，之后再纳入更早的轮次也不改变它。
		if cutoffID == 0 {
			cutoffID = turn[len(turn)-1].ID
		}

		// 前置拼接（先复制一份再 append，避免复用 turn 的底层数组）。
		merged := make([]Message, 0, len(turn)+len(picked))
		merged = append(merged, turn...)
		merged = append(merged, picked...)
		picked = merged
	}

	if len(picked) == 0 {
		// 单轮就超过 maxChars：不压缩，交给预算硬截断兜底。
		return Window{Keep: flatten(turns)}
	}

	return Window{
		ToCompress: picked,
		Keep:       flatten(turns[keepFrom:]),
		CutoffID:   cutoffID,
	}
}

// groupTurns 把消息按轮分组。
// 开头的 assistant 消息（理论上不该出现）自成一轮，避免被丢弃。
func groupTurns(messages []Message) [][]Message {
	var (
		turns [][]Message
		cur   []Message
	)

	for _, m := range messages {
		if m.IsUser() {
			if len(cur) > 0 {
				turns = append(turns, cur)
			}
			cur = []Message{m}
			continue
		}
		if len(cur) == 0 {
			// 开头的 assistant 消息单独成组
			turns = append(turns, []Message{m})
			continue
		}
		cur = append(cur, m)
	}

	if len(cur) > 0 {
		turns = append(turns, cur)
	}
	return turns
}

// flatten 把分组展平。
func flatten(turns [][]Message) []Message {
	var out []Message
	for _, t := range turns {
		out = append(out, t...)
	}
	return out
}

// turnCharCount 统计一轮的字符总数。
func turnCharCount(turn []Message) int {
	n := 0
	for _, m := range turn {
		n += len([]rune(m.Content))
	}
	return n
}

// renderConversation 把消息渲染成压缩提示词里的对话文本。
func renderConversation(msgs []Message) string {
	var b strings.Builder
	for _, m := range msgs {
		role := "学生"
		if m.IsAssistant() {
			role = "辅导员"
		}
		b.WriteString(role)
		b.WriteString("：")
		b.WriteString(strings.TrimSpace(m.Content))
		b.WriteString("\n\n")
	}
	return b.String()
}

// MaybeCompress 按阈值决定并执行滚动压缩。
// 失败只记 warn：第 3 步的 token 预算硬截断会兜底，对话仍可用。
func (s *Summarizer) MaybeCompress(ctx context.Context, sessionID string, currentMsgID uint64, currentQuestion string, systemTokens int) CompressResult {
	sess, err := s.sess.GetSession(ctx, sessionID)
	if err != nil {
		s.log.Warn("读取会话失败，跳过压缩", zap.Error(err))
		return CompressResult{}
	}

	all, err := s.sess.ListMessagesAfter(ctx, sessionID, sess.SummaryCursor)
	if err != nil {
		s.log.Warn("读取未压缩消息失败，跳过压缩", zap.Error(err))
		return CompressResult{}
	}

	// 排除本轮当前消息：它要被保留，不属于可压缩的历史。
	msgs := make([]Message, 0, len(all))
	for _, m := range all {
		if m.ID == currentMsgID {
			continue
		}
		// 空失败消息不入压缩源，避免污染摘要。
		if m.Status == "failed" && strings.TrimSpace(m.Content) == "" {
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

	ok, reason := s.ShouldCompress(u)
	if !ok {
		// 保留判断依据，便于线上排查「为什么没压缩」。
		s.log.Debug("未达压缩阈值",
			zap.Int("messages", len(msgs)),
			zap.Int("trigger_messages", s.cfg.CompressTriggerMessages),
			zap.Int("tokens", s.EffectiveTokens(u)),
			zap.Int("trigger_tokens", s.cfg.CompressTriggerTokens),
		)
		return CompressResult{Reason: "below_threshold"}
	}

	win := selectWindow(msgs, s.cfg.KeepRecentTurns, s.cfg.CompressSourceMaxChars)
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

	// 压缩后重算基线。
	//
	// 这里有个容易踩的坑：eino 会在真实 prompt 里注入工具 Schema 与技能清单，
	// 这部分固定开销（实测约 3k token）本地估算器完全看不到。
	// 若直接用「本地估算的 system + 摘要 + 保留原文」当新基线，
	// 算出来会远低于真实值（实测估算 3612 vs 真实 6803），
	// 于是下一轮立刻又超阈值、反复压缩却始终降不下来。
	//
	// 正确做法：从真实基线里剥离「可压缩部分」（旧摘要 + 被压缩的原文），
	// 保留不可压缩的固定开销，再加上压缩后的新内容。
	fixedOverhead := 0
	if sess.ContextTokens > 0 {
		// 真实基线 = 固定开销 + 旧摘要 + 压缩前的全部历史 + 上一轮输入
		compressible := s.counter.Estimate(sess.Summary) +
			s.counter.EstimateMessages(win.ToCompress) +
			s.counter.EstimateMessages(win.Keep)
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
		s.counter.Estimate(summary) +
		s.counter.EstimateMessages(win.Keep) +
		s.counter.Estimate(currentQuestion)

	applied, err := s.sess.UpdateSummary(ctx, sessionID, summary, win.CutoffID, newBaseline)
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

	s.log.Info("上下文已压缩",
		zap.String("reason", reason),
		zap.Uint64("cutoff", win.CutoffID),
		zap.Int("compressed_msgs", len(win.ToCompress)),
		zap.Int("kept_msgs", len(win.Keep)),
		zap.Int("baseline_tokens", newBaseline),
		zap.Int("fixed_overhead", fixedOverhead),
		zap.Int("prev_context_tokens", sess.ContextTokens),
	)

	return CompressResult{
		Triggered:     true,
		Reason:        reason,
		Compressed:    true,
		Summary:       summary,
		Cursor:        win.CutoffID,
		ContextTokens: newBaseline,
	}
}

// compress 调用 LLM 生成滚动摘要。
func (s *Summarizer) compress(ctx context.Context, prevSummary string, msgs []Message) (string, error) {
	var b strings.Builder

	b.WriteString("## 已有摘要\n\n")
	if strings.TrimSpace(prevSummary) == "" {
		b.WriteString("（无，本段是会话开头）\n")
	} else {
		b.WriteString(prevSummary)
		b.WriteString("\n")
	}

	b.WriteString("\n## 需要并入摘要的新对话\n\n")
	b.WriteString(renderConversation(msgs))
	b.WriteString("请输出合并后的完整摘要。")

	return s.model.Complete(ctx, summarizePrompt, b.String())
}
