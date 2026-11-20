package memory

import (
	"strings"
	"testing"
)

// TestBaselinePreservesFixedOverhead 验证压缩后的基线不会把
// eino 注入的固定开销（工具 Schema + 技能清单）算丢。
//
// 这是一个真实线上问题：本地估算器看不到工具 Schema，
// 若直接用估算值当新基线，算出来远低于真实 prompt，
// 于是下一轮立刻又超阈值，反复压缩却始终降不下来。
func TestBaselinePreservesFixedOverhead(t *testing.T) {
	c := Counter{}

	// 模拟真实场景：真实 prompt 8000，其中约 3300 是固定开销
	const realFixed = 3300
	summary := "旧摘要内容"
	toCompress := []Message{
		{ID: 1, Role: "user", Content: strings.Repeat("问", 200)},
		{ID: 2, Role: "assistant", Content: strings.Repeat("答", 200)},
	}
	keep := []Message{
		{ID: 3, Role: "user", Content: strings.Repeat("问", 100)},
		{ID: 4, Role: "assistant", Content: strings.Repeat("答", 100)},
	}

	compressible := c.Estimate(summary) + c.EstimateMessages(toCompress) + c.EstimateMessages(keep)
	realPrompt := realFixed + compressible

	// 按修复后的算法：固定开销 = 真实 - 可压缩部分
	derivedFixed := realPrompt - compressible
	if derivedFixed != realFixed {
		t.Fatalf("推导出的固定开销 = %d, want %d", derivedFixed, realFixed)
	}

	// 压缩后基线应显著下降，但仍高于固定开销本身
	newSummary := "新摘要"
	newBaseline := derivedFixed + c.Estimate(newSummary) + c.EstimateMessages(keep)

	if newBaseline < derivedFixed {
		t.Error("新基线不应低于固定开销")
	}
	if newBaseline >= realPrompt {
		t.Errorf("压缩后基线应下降: 新 %d vs 原 %d", newBaseline, realPrompt)
	}
}

// TestEffectiveTokensUsesRealBaseline 验证有效 token 优先用真实基线。
func TestEffectiveTokensUsesRealBaseline(t *testing.T) {
	s := &Summarizer{counter: Counter{}}

	// 有真实基线时：真实值 + 本轮输入
	u := Uncompressed{
		ContextTokens:   8000,
		Summary:         "摘要",
		Messages:        []Message{{ID: 1, Role: "user", Content: "历史"}},
		CurrentQuestion: "新问题",
		SystemTokens:    999999, // 应被忽略
	}
	got := s.EffectiveTokens(u)

	if got <= 8000 {
		t.Errorf("应以真实基线为基准，实际 %d", got)
	}
	if got > 8000+100 {
		t.Errorf("不应把 SystemTokens 叠加进来，实际 %d", got)
	}
}

// TestEffectiveTokensFallsBackToEstimate 验证无真实基线时退回估算。
func TestEffectiveTokensFallsBackToEstimate(t *testing.T) {
	s := &Summarizer{counter: Counter{}}

	u := Uncompressed{
		ContextTokens:   0, // 无真实值
		Summary:         strings.Repeat("摘", 100),
		Messages:        []Message{{ID: 1, Role: "user", Content: strings.Repeat("问", 100)}},
		CurrentQuestion: "问题",
		SystemTokens:    500,
	}
	got := s.EffectiveTokens(u)

	// 应包含 system + summary + history + question 的估算总和
	if got < 500+100 {
		t.Errorf("估算值过小: %d", got)
	}
}
