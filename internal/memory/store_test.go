package memory

import (
	"strings"
	"testing"
)

func TestStripCodeFence(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"无围栏", "## 学习背景\n内容", "## 学习背景\n内容"},
		{"markdown 围栏", "```markdown\n## 学习背景\n内容\n```", "## 学习背景\n内容"},
		{"无语言标记", "```\nhello\n```", "hello"},
		{"只有起始围栏", "```markdown", ""},
		{"围栏后有多余空行", "```md\n\n## A\n\nx\n\n```\n", "## A\n\nx"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := StripCodeFence(tc.in); got != tc.want {
				t.Errorf("StripCodeFence(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

// TestValidateMemoryDoc 验证结构校验：空内容或缺少固定标题时拒绝写入。
func TestValidateMemoryDoc(t *testing.T) {
	if ValidateMemoryDoc("") {
		t.Error("空内容应校验失败")
	}
	if ValidateMemoryDoc("   \n  ") {
		t.Error("空白内容应校验失败")
	}
	if ValidateMemoryDoc("这是一段没有标题的自由文本") {
		t.Error("缺少固定标题应校验失败")
	}
	if !ValidateMemoryDoc("## 学习背景\n\n计算机专业") {
		t.Error("含固定标题应校验通过")
	}
}

// TestPruneEmptySections 验证空小节被剔除、有内容的小节保留。
func TestPruneEmptySections(t *testing.T) {
	in := `## 学习背景

计算机专业大三

## 长期目标

## 学习偏好

喜欢先看代码

## 薄弱知识点

## 交互约定
`
	got := PruneEmptySections(in)

	if strings.Contains(got, "长期目标") {
		t.Error("空小节「长期目标」应被剔除")
	}
	if strings.Contains(got, "薄弱知识点") {
		t.Error("空小节「薄弱知识点」应被剔除")
	}
	if !strings.Contains(got, "计算机专业大三") {
		t.Error("应有内容的小节被误删")
	}
	if !strings.Contains(got, "喜欢先看代码") {
		t.Error("应有内容的小节被误删")
	}
}

// TestPruneEmptySectionsKeepsAllWhenFull 验证内容齐全时不做删减。
func TestPruneEmptySectionsKeepsAllWhenFull(t *testing.T) {
	in := EmptyMemoryDoc()
	for _, sec := range MemorySections {
		in = strings.Replace(in, "## "+sec+"\n\n", "## "+sec+"\n\n有内容\n\n", 1)
	}

	got := PruneEmptySections(in)
	for _, sec := range MemorySections {
		if !strings.Contains(got, sec) {
			t.Errorf("节 %q 不应被剔除", sec)
		}
	}
}

// TestAppendPending 验证待整合条目的追加与去重结构。
func TestAppendPending(t *testing.T) {
	// 从空文档开始：应自动建出待整合小节
	got := AppendPending("", "偏好先看代码", "2026-11-20")
	if !strings.Contains(got, "## "+PendingSection) {
		t.Error("应创建待整合小节")
	}
	if !strings.Contains(got, "偏好先看代码") {
		t.Error("应包含追加的条目")
	}
	if !strings.Contains(got, "2026-11-20") {
		t.Error("应包含日期")
	}

	// 再次追加：应累积两条，且只保留一个小节标题
	got = AppendPending(got, "目标是大厂后端", "2026-11-21")
	if n := strings.Count(got, "## "+PendingSection); n != 1 {
		t.Errorf("待整合小节应只有一个，实际 %d", n)
	}
	if !strings.Contains(got, "偏好先看代码") || !strings.Contains(got, "目标是大厂后端") {
		t.Error("两条条目都应保留")
	}

	if !HasPending(got) {
		t.Error("HasPending 应为 true")
	}
}

// TestClearPending 验证清空待整合内容但保留标题。
func TestClearPending(t *testing.T) {
	doc := AppendPending("## 学习背景\n\n计算机专业", "偏好先看代码", "2026-11-20")
	if !HasPending(doc) {
		t.Fatal("前置条件：应有待整合内容")
	}

	cleared := ClearPending(doc)
	if HasPending(cleared) {
		t.Error("清空后不应再有待整合内容")
	}
	if !strings.Contains(cleared, "## "+PendingSection) {
		t.Error("清空后应保留待整合标题")
	}
	if !strings.Contains(cleared, "计算机专业") {
		t.Error("不应影响其他小节")
	}
}

// TestTrimToMaxChars 验证按字符截断且不切坏太多内容。
func TestTrimToMaxChars(t *testing.T) {
	long := strings.Repeat("中", 100)
	got := TrimToMaxChars(long, 10)
	if n := len([]rune(got)); n > 10 {
		t.Errorf("截断后应不超过 10 字符，实际 %d", n)
	}

	// 未超限时原样返回
	short := "短文本"
	if got := TrimToMaxChars(short, 10); got != short {
		t.Errorf("未超限时应原样返回，实际 %q", got)
	}

	// maxChars<=0 表示不限制
	if got := TrimToMaxChars(long, 0); got != long {
		t.Error("maxChars<=0 时不应截断")
	}
}
