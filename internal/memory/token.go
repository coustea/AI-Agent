// Package memory 实现 Pre-Run 阶段的记忆提取、上下文压缩与上下文重建。
//
// 本包不依赖 eino agent，也不依赖 Gin：它只面对消息切片、Markdown 文档和
// 一个最小的 LLM 接口，因此可以被单元测试完全覆盖。
package memory

import (
	"unicode"
	"unicode/utf8"
)

// Counter 估算 token 数。
//
// 说明：这里刻意用本地估算器而非 tiktoken 之类的精确分词：
//   - 精确分词依赖具体模型，且引入额外依赖与 CPU 开销；
//   - 本项目的阈值判断只需要「同量级的近似值」，真实用量由模型返回的
//     Usage 覆盖（见 harness 里把 TotalTokens 写回 context_tokens）。
//
// 估算规则按字符类别加权：
//   - ASCII 字母数字：约 4 字符 / token
//   - 中日韩等表意文字：约 1 字符 / token（这些字符 token 密度高）
//   - 空白与标点：约 4 字符 / token
type Counter struct{}

// Estimate 估算单个字符串的 token 数。
func (Counter) Estimate(s string) int {
	if s == "" {
		return 0
	}

	var ascii, wide, spaces int
	for _, r := range s {
		switch {
		case r == ' ' || r == '\n' || r == '\t' || r == '\r':
			spaces++
		case r < utf8.RuneSelf:
			// ASCII 的可打印字符按 4:1 折算
			ascii++
		case unicode.Is(unicode.Han, r), unicode.Is(unicode.Hiragana, r),
			unicode.Is(unicode.Katakana, r), unicode.Is(unicode.Hangul, r):
			wide++
		default:
			// 其他非 ASCII（全角标点、emoji 等）按较宽处理
			wide++
		}
	}

	// 每一步都用整数向上取整，避免小数累积误差。
	tokens := (ascii+3)/4 + wide + (spaces+3)/4

	// 极短字符串至少算 1 个 token，避免全空白被算成 0。
	if tokens == 0 {
		tokens = 1
	}
	return tokens
}

// EstimateMessages 估算一组 (role, content) 的 token 总量。
// 每条消息额外加 4 个 token 的固定开销（角色标记、分隔符等）。
func (c Counter) EstimateMessages(msgs []Message) int {
	total := 0
	for _, m := range msgs {
		total += c.Estimate(m.Content) + 4
	}
	return total
}

// Message 是 memory 包内部使用的轻量消息表示，
// 避免让本包依赖 model 或 schema，从而保持可测试性。
type Message struct {
	ID      uint64
	Role    string
	Content string
	Status  string
}

// IsUser 判断是否用户消息。
func (m Message) IsUser() bool { return m.Role == "user" }

// IsAssistant 判断是否助手消息。
func (m Message) IsAssistant() bool { return m.Role == "assistant" }

// CountTurns 统计 user 消息条数，即「轮数」。
func CountTurns(msgs []Message) int {
	n := 0
	for _, m := range msgs {
		if m.IsUser() {
			n++
		}
	}
	return n
}
