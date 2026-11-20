// Package window 负责上下文窗口的裁剪与 token 估算。
//
// 这是纯计算层：不读数据库、不调模型、不碰网络。
// 输入一组消息与预算，输出「这一轮该喂给模型的历史」。
// 因此它可以被单元测试完全覆盖，也最容易验证正确性。
package window

import (
	"unicode"
	"unicode/utf8"

	"mentorly/internal/dialogue"
)

// Counter 估算 token 数。
//
// 说明：这里刻意用本地估算器而非 tiktoken 之类的精确分词：
//   - 精确分词依赖具体模型，且引入额外依赖与 CPU 开销；
//   - 阈值判断只需要「同量级的近似值」，真实用量由模型返回的
//     Usage 覆盖（turn 编排时把 TotalTokens 写回 context_tokens）。
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
			ascii++
		case unicode.Is(unicode.Han, r), unicode.Is(unicode.Hiragana, r),
			unicode.Is(unicode.Katakana, r), unicode.Is(unicode.Hangul, r):
			wide++
		default:
			wide++
		}
	}

	// 每一步都用整数向上取整，避免小数累积误差。
	tokens := (ascii+3)/4 + wide + (spaces+3)/4
	if tokens == 0 {
		tokens = 1
	}
	return tokens
}

// EstimateMessages 估算一组消息的 token 总量。
// 每条消息额外加 4 个 token 的固定开销（角色标记、分隔符等）。
func (c Counter) EstimateMessages(msgs []dialogue.Message) int {
	total := 0
	for _, m := range msgs {
		total += c.Estimate(m.Content) + 4
	}
	return total
}
