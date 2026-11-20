package tutor

import (
	_ "embed"
	"strings"
)

//go:embed prompt.md
var basePrompt string

// BasePrompt 返回静态 System Prompt 底座。
func BasePrompt() string {
	return strings.TrimSpace(basePrompt)
}

// PromptInput 是动态 System Prompt 的拼装入参。
//
// 核心原则（Zero Empty Noise）：任何一段没有内容就不注入，
// 新会话不会因此多付 token。
type PromptInput struct {
	// Base 静态底座，留空则用 BasePrompt()
	Base string
	// Now 当前日期
	Now string
	// Workspace 工作区文件索引
	Workspace []string
	// Vision 模型是否支持图片输入
	Vision bool
}

// AssemblePrompt 按需拼装 System Prompt。
//
// 这是全系统唯一的 Prompt 拼装实现：Agent、Harness、Skill 都从这里取，
// 避免同一个 Prompt 在多处各拼一遍、内容还不一致。
func AssemblePrompt(in PromptInput) string {
	var sb strings.Builder

	base := strings.TrimSpace(in.Base)
	if base == "" {
		base = BasePrompt()
	}
	sb.WriteString(base)

	if in.Now != "" {
		sb.WriteString("\n\n## 当前日期\n\n")
		sb.WriteString(in.Now)
	}

	if len(in.Workspace) > 0 {
		sb.WriteString("\n\n## 工作区文件\n\n")
		sb.WriteString("`/workspace` 中已有以下文件，可直接读取：\n")
		for _, f := range in.Workspace {
			sb.WriteString("- /workspace/")
			sb.WriteString(f)
			sb.WriteString("\n")
		}
	}

	if in.Vision {
		sb.WriteString("\n\n## 图片输入\n\n")
		sb.WriteString("当前模型支持图片直接输入。用户上传的图片已在对话中呈现，可直接理解，无需调用工具读取。")
	}

	return sb.String()
}
