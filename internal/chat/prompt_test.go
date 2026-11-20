package chat

import (
	"strings"
	"testing"
)

// TestBasePromptNotEmpty 验证静态底座存在且足够精简。
func TestBasePromptNotEmpty(t *testing.T) {
	p := BasePrompt()
	if strings.TrimSpace(p) == "" {
		t.Fatal("tutor.md 不应为空")
	}

	// 计划要求精简底座：不写工具参数说明书（工具用法由 eino Schema 承担）。
	for _, forbidden := range []string{"参数说明", "argumentsInJSON", "JSON Schema"} {
		if strings.Contains(p, forbidden) {
			t.Errorf("静态 Prompt 不应包含工具参数说明：%q", forbidden)
		}
	}

	// 但必须包含导师身份
	if !strings.Contains(p, "辅导员") {
		t.Error("应包含导师身份说明")
	}
}

// TestAssemblePromptZeroEmptyNoise 验证空记忆/空摘要/空工作区都不注入。
func TestAssemblePromptZeroEmptyNoise(t *testing.T) {
	got := AssemblePrompt(PromptInput{
		Base: "底座",
		Now:  "2026-11-20",
		// MemoryDoc / Summary / WorkspaceFiles 全空
	})

	if !strings.Contains(got, "底座") {
		t.Error("应包含底座")
	}
	if !strings.Contains(got, "2026-11-20") {
		t.Error("当前日期应始终注入")
	}

	// 三个可选段落都不应出现
	for _, unwanted := range []string{"关于这位学生", "会话摘要", "工作区文件"} {
		if strings.Contains(got, unwanted) {
			t.Errorf("空内容不应注入 %q 段落", unwanted)
		}
	}
}

// TestAssemblePromptWithContent 验证有内容时对应段落被注入。
func TestAssemblePromptWithContent(t *testing.T) {
	got := AssemblePrompt(PromptInput{
		Base:           "底座",
		Now:            "2026-11-20",
		Summary:        "已讨论 TCP 三次握手",
		WorkspaceFiles: []string{"notes.md", "demo.go"},
	})

	for _, want := range []string{
		"会话摘要", "TCP 三次握手",
		"工作区文件", "/workspace/notes.md", "/workspace/demo.go",
	} {
		if !strings.Contains(got, want) {
			t.Errorf("应包含 %q", want)
		}
	}
}
