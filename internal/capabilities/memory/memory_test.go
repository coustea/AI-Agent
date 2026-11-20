package memory

import (
	"strings"
	"testing"
)

// TestNormalizeKind 校验类别归一化，脏数据不应进入分类统计。
func TestNormalizeKind(t *testing.T) {
	cases := map[string]string{
		KindFact:       KindFact,
		KindPreference: KindPreference,
		KindWeakness:   KindWeakness,
		KindGoal:       KindGoal,
		"prefer":       KindPreference,
		"style":        KindPreference,
		"weak":         KindWeakness,
		"gap":          KindWeakness,
		"target":       KindGoal,
		"plan":         KindGoal,
		"unknown":      KindFact,
		"":             KindFact,
	}
	for in, want := range cases {
		if got := normalizeKind(in); got != want {
			t.Errorf("normalizeKind(%q) = %q, 期望 %q", in, got, want)
		}
	}
}

// TestEscapeLike 校验 LIKE 通配符转义。
//
// 不转义时，用户输入 "%" 会匹配全部记忆，
// 输入 "_" 会匹配任意单字符，检索结果被放大。
func TestEscapeLike(t *testing.T) {
	cases := map[string]string{
		"50%":    `50\%`,
		"a_b":    `a\_b`,
		`a\b`:    `a\\b`,
		"normal": "normal",
	}
	for in, want := range cases {
		if got := escapeLike(in); got != want {
			t.Errorf("escapeLike(%q) = %q, 期望 %q", in, got, want)
		}
	}
}

// TestDefaultSource 未指定来源时默认为 inferred。
func TestDefaultSource(t *testing.T) {
	if got := defaultSource("explicit"); got != "explicit" {
		t.Errorf("显式来源 = %q", got)
	}
	if got := defaultSource(""); got != "inferred" {
		t.Errorf("空来源 = %q, 期望 inferred", got)
	}
	if got := defaultSource("whatever"); got != "inferred" {
		t.Errorf("未知来源 = %q, 期望 inferred", got)
	}
}

// TestMaxContentChars 记忆长度上限必须合理：
// 记忆是一句话，不是一段对话。
func TestMaxContentChars(t *testing.T) {
	if maxContentChars <= 0 || maxContentChars > 1000 {
		t.Errorf("maxContentChars = %d，应在一个合理区间", maxContentChars)
	}
}

// TestMemoryKindConstants 常量之间不能重复，否则分类会合并。
func TestMemoryKindConstants(t *testing.T) {
	kinds := []string{KindFact, KindPreference, KindWeakness, KindGoal}
	seen := make(map[string]bool)
	for _, k := range kinds {
		if seen[k] {
			t.Errorf("重复的类别常量: %q", k)
		}
		seen[k] = true
		if strings.TrimSpace(k) == "" {
			t.Error("类别常量不能为空")
		}
	}
}
