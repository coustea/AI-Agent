package chat

import (
	"strings"
	"testing"
)

// TestNewBaselineStripsFixedOverhead 是压缩基线的关键回归测试。
//
// 背景：eino 会在真实 prompt 里注入工具 Schema 与技能清单，
// 这部分固定开销（实测约 4.5-5k token）本地估算器完全看不到。
// 若直接用「估算的 summary + 原文」当新基线，会算出远低于真实值的数
// （实测估算 3612 vs 真实 6803），导致下一轮立刻又超阈值、反复压缩降不下来。
//
// 正确做法是从真实基线里剥离可压缩部分，保留固定开销。
func TestNewBaselineStripsFixedOverhead(t *testing.T) {
	const (
		prevContextTokens = 6803    // 模型返回的真实基线
		prevSummary       = "旧摘要内容" // 约 5 token
	)

	compressed := []Message{
		{ID: 1, Role: RoleUser, Content: strings.Repeat("压缩", 100)},
		{ID: 2, Role: RoleAssistant, Content: strings.Repeat("回答", 100)},
	}
	kept := []Message{
		{ID: 3, Role: RoleUser, Content: "保留的问题"},
		{ID: 4, Role: RoleAssistant, Content: "保留的回答"},
	}

	baseline, fixedOverhead := newBaseline(
		prevContextTokens, prevSummary,
		compressed, kept,
		"新摘要", "本轮新问题",
		4000, testCounter,
	)

	// 固定开销应接近真实基线与估算可压缩部分之差，远大于 0。
	if fixedOverhead <= 0 {
		t.Errorf("固定开销应大于 0，实际 %d", fixedOverhead)
	}
	if fixedOverhead >= prevContextTokens {
		t.Errorf("固定开销不应超过真实基线，实际 %d", fixedOverhead)
	}

	// 新基线应显著小于压缩前的真实基线（压缩的目的就是降下来）。
	if baseline >= prevContextTokens {
		t.Errorf("压缩后基线 %d 应小于压缩前 %d", baseline, prevContextTokens)
	}
	// 但也不能小到忽略固定开销：必须至少包含 fixedOverhead。
	if baseline < fixedOverhead {
		t.Errorf("基线 %d 不应小于固定开销 %d", baseline, fixedOverhead)
	}
}

// TestNewBaselineWithoutRealUsage 验证尚无真实用量时退回纯估算。
func TestNewBaselineWithoutRealUsage(t *testing.T) {
	baseline, fixedOverhead := newBaseline(
		0, "", // 无真实基线
		nil, nil,
		"摘要", "问题",
		4000, testCounter,
	)

	if fixedOverhead != 4000 {
		t.Errorf("无真实用量时应使用 systemTokens，实际 %d", fixedOverhead)
	}
	if baseline <= fixedOverhead {
		t.Errorf("基线应包含固定开销 + 内容，实际 %d", baseline)
	}
}

// TestShouldCompressByMessages 验证按消息条数触发。
func TestShouldCompressByMessages(t *testing.T) {
	cfg := Config{CompressTriggerMessages: 4, CompressTriggerTokens: 100000}
	msgs := []Message{
		{ID: 1, Role: RoleUser, Content: "a"},
		{ID: 2, Role: RoleAssistant, Content: "b"},
		{ID: 3, Role: RoleUser, Content: "c"},
		{ID: 4, Role: RoleAssistant, Content: "d"},
	}

	ok, reason := shouldCompress(uncompressed{Messages: msgs}, cfg, testCounter)
	if !ok {
		t.Error("达到消息阈值应触发")
	}
	if !strings.Contains(reason, "messages=") {
		t.Errorf("原因应说明消息条数，实际 %q", reason)
	}
}

// TestShouldCompressEmpty 验证无消息时不触发（避免每次白跑 LLM）。
func TestShouldCompressEmpty(t *testing.T) {
	cfg := Config{CompressTriggerMessages: 1, CompressTriggerTokens: 1}
	ok, _ := shouldCompress(uncompressed{}, cfg, testCounter)
	if ok {
		t.Error("无消息时不应触发压缩")
	}
}

// TestEffectiveTokensPrefersRealUsage 验证优先用真实用量。
func TestEffectiveTokensPrefersRealUsage(t *testing.T) {
	u := uncompressed{
		ContextTokens:   5000,
		SystemTokens:    1000,
		Summary:         "摘要",
		Messages:        []Message{{ID: 1, Role: RoleUser, Content: "历史"}},
		CurrentQuestion: "新问题",
	}

	got := effectiveTokens(u, testCounter)
	if got <= 5000 {
		t.Errorf("应包含真实基线 + 新输入，实际 %d", got)
	}
	// 不应把 SystemTokens 叠加进去（真实用量已含）。
	if got >= 5000+1000 {
		t.Errorf("不应重复叠加 systemTokens，实际 %d", got)
	}
}

// TestStripCodeFence 验证去掉模型包裹的代码围栏。
func TestStripCodeFence(t *testing.T) {
	cases := []struct{ in, want string }{
		{"```\n内容\n```", "内容"},
		{"```markdown\n内容\n```", "内容"},
		{"无围栏", "无围栏"},
	}
	for _, c := range cases {
		if got := StripCodeFence(c.in); got != c.want {
			t.Errorf("StripCodeFence(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

// TestCounterEstimate 验证 token 估算量级合理。
func TestCounterEstimate(t *testing.T) {
	// ASCII 约 4 字符 1 token
	if got := testCounter.Estimate("abcdefgh"); got != 2 {
		t.Errorf("8 个 ASCII 字符应约 2 token，实际 %d", got)
	}
	// 中文约 1 字符 1 token
	if got := testCounter.Estimate("中文测试"); got != 4 {
		t.Errorf("4 个汉字应约 4 token，实际 %d", got)
	}
	if got := testCounter.Estimate(""); got != 0 {
		t.Errorf("空串应为 0，实际 %d", got)
	}
}
