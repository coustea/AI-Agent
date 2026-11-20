package window

import (
	"strings"

	"mentorly/internal/dialogue"
)

// Budget 是历史裁剪的预算参数。
type Budget struct {
	// MaxMessages 历史消息条数上限
	MaxMessages int
	// Tokens 历史 token 预算（已扣除 System Prompt 与本轮问题）
	Tokens int
}

// Fit 从最新消息往前按预算保留历史，并做对话结构修正。
//
// 规则：
//   - 从最新往前累加，超过预算即停止；
//   - 跳过「失败且无内容」的消息；
//   - 结果必须以 user 开头（丢弃开头的 assistant 孤儿消息）；
//   - user / assistant 必须交替，丢弃连续的同类消息（保留更早的那条，
//     因为连续的 assistant 中间被丢掉的往往是工具调用轮次）。
//
// 返回保留下来的消息与它们的估算 token 总量。
func Fit(msgs []dialogue.Message, b Budget, c Counter) ([]dialogue.Message, int) {
	if len(msgs) == 0 {
		return nil, 0
	}
	maxMessages := b.MaxMessages
	if maxMessages <= 0 {
		maxMessages = 40
	}

	// 1. 从后往前按预算（与条数上限）收集。
	var picked []dialogue.Message
	tokens := 0

	for i := len(msgs) - 1; i >= 0; i-- {
		m := msgs[i]

		if m.IsEmptyFailure() {
			continue
		}

		mt := c.Estimate(m.Content) + 4
		if len(picked) >= maxMessages {
			break
		}

		// 预算不足时仍要保留至少一条：没有历史上下文，模型会完全失去对话感。
		// 这里对第一条无条件收录，之后才严格按预算停止。
		if tokens+mt > b.Tokens && len(picked) > 0 {
			break
		}

		tokens += mt
		picked = append(picked, m)
	}

	// 2. 反转回时间升序。
	reverse(picked)

	// 3. 若收集到的片段全是 assistant（预算只够最后一条回答），
	// 继续往前补一条 user，否则 normalize 会把它整段丢弃，
	// 结果就是「有预算但零上下文」——这比稍微超预算更糟。
	if !hasUser(picked) && len(picked) > 0 {
		firstID := picked[0].ID
		for i := len(msgs) - 1; i >= 0; i-- {
			m := msgs[i]
			if m.ID >= firstID || m.IsEmptyFailure() {
				continue
			}
			if m.IsUser() {
				picked = append([]dialogue.Message{m}, picked...)
				tokens += c.Estimate(m.Content) + 4
				break
			}
		}
	}

	// 4. 修正结构：以 user 开头，user/assistant 交替。
	return normalize(picked, c)
}

// normalize 让消息切片以 user 开头且 user/assistant 交替。
func normalize(msgs []dialogue.Message, c Counter) ([]dialogue.Message, int) {
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

	out := make([]dialogue.Message, 0, len(msgs)-start)
	var lastRole string

	for _, m := range msgs[start:] {
		// 同类消息连发：保留先出现的那条，跳过后续的。
		if m.Role == lastRole {
			continue
		}
		out = append(out, m)
		lastRole = m.Role
	}

	// 若以 assistant 结尾，说明最后一条回答没有后续问题，
	// 这是正常历史（下一轮的问题会追加在它后面），无需处理。

	return out, c.EstimateMessages(out)
}

// SelectForCompression 是压缩窗口的切分结果。
type SelectResult struct {
	// ToCompress 需要送入压缩的旧消息（整轮为界，时间升序）
	ToCompress []dialogue.Message
	// Keep 保留原文的最近消息
	Keep []dialogue.Message
	// CutoffID 送入压缩的最后一条消息 id，用作新的 summary_cursor；0 表示不压缩
	CutoffID uint64
}

// SelectForCompression 是纯函数：切分「送去压缩」与「保留原文」的边界。
//
// 规则：
//  1. 保留最近 keepRecentTurns 轮原文（一轮指从一条 user 消息到其后的 assistant 回复）；
//  2. 边界之前、且总字符数不超过 maxChars 的消息送去压缩；
//  3. 按**整轮**截断：一旦某一轮放不下，就停止，不再尝试更早的轮次，
//     避免把同一轮拆成「压缩一半、保留一半」导致语义断裂。
//
// 调用方需保证 messages 已排除本轮当前消息，且按 id 升序。
func SelectForCompression(messages []dialogue.Message, keepRecentTurns, maxChars int) SelectResult {
	if len(messages) == 0 {
		return SelectResult{}
	}
	if keepRecentTurns < 0 {
		keepRecentTurns = 0
	}

	// 1. 按「轮」分组：每条 user 消息开启一轮，后续 assistant 消息归入该轮。
	turns := GroupTurns(messages)

	// 2. 从后往前保留 keepRecentTurns 轮。
	keepFrom := len(turns) - keepRecentTurns
	if keepFrom < 0 {
		keepFrom = 0
	}

	candidates := turns[:keepFrom]
	if len(candidates) == 0 {
		// 全部轮次都要保留原文，无可压缩内容。
		return SelectResult{Keep: Flatten(turns)}
	}

	// 3. 从最新一轮往前累加，超过 maxChars 即停止（按整轮截断）。
	var (
		picked   []dialogue.Message
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
		merged := make([]dialogue.Message, 0, len(turn)+len(picked))
		merged = append(merged, turn...)
		merged = append(merged, picked...)
		picked = merged
	}

	if len(picked) == 0 {
		// 单轮就超过 maxChars：不压缩，交给预算硬截断兜底。
		return SelectResult{Keep: Flatten(turns)}
	}

	return SelectResult{
		ToCompress: picked,
		Keep:       Flatten(turns[keepFrom:]),
		CutoffID:   cutoffID,
	}
}

// GroupTurns 把消息按轮分组。
// 开头的 assistant 消息（理论上不该出现）自成一轮，避免被丢弃。
func GroupTurns(messages []dialogue.Message) [][]dialogue.Message {
	var (
		turns [][]dialogue.Message
		cur   []dialogue.Message
	)

	for _, m := range messages {
		if m.IsUser() {
			if len(cur) > 0 {
				turns = append(turns, cur)
			}
			cur = []dialogue.Message{m}
			continue
		}
		if len(cur) == 0 {
			// 开头的 assistant 消息单独成组
			turns = append(turns, []dialogue.Message{m})
			continue
		}
		cur = append(cur, m)
	}

	if len(cur) > 0 {
		turns = append(turns, cur)
	}
	return turns
}

// Flatten 把分组展平。
func Flatten(turns [][]dialogue.Message) []dialogue.Message {
	var out []dialogue.Message
	for _, t := range turns {
		out = append(out, t...)
	}
	return out
}

// turnCharCount 统计一轮的字符总数。
func turnCharCount(turn []dialogue.Message) int {
	n := 0
	for _, m := range turn {
		n += len([]rune(m.Content))
	}
	return n
}

// Render 把消息渲染成「学生/辅导员」对话文本，供压缩与记忆提示词使用。
func Render(msgs []dialogue.Message, userLabel, assistantLabel string) string {
	var b strings.Builder
	for _, m := range msgs {
		role := userLabel
		if m.IsAssistant() {
			role = assistantLabel
		}
		b.WriteString(role)
		b.WriteString("：")
		b.WriteString(strings.TrimSpace(m.Content))
		b.WriteString("\n\n")
	}
	return b.String()
}

// reverse 原地反转。
func reverse(msgs []dialogue.Message) {
	for i, j := 0, len(msgs)-1; i < j; i, j = i+1, j-1 {
		msgs[i], msgs[j] = msgs[j], msgs[i]
	}
}

// hasUser 判断切片里是否含 user 消息。
func hasUser(msgs []dialogue.Message) bool {
	for _, m := range msgs {
		if m.IsUser() {
			return true
		}
	}
	return false
}
