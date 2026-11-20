package agent

import (
	_ "embed"
	"strings"
)

//go:embed prompts/tutor.md
var tutorPrompt string

// BasePrompt 返回静态 System Prompt 底座。
// 动态段落（记忆、摘要、工作区索引）由 memory.Builder 追加，本函数只给底座。
func BasePrompt() string {
	return strings.TrimSpace(tutorPrompt)
}

// PromptInput 是动态 Prompt 拼装的入参，主要供测试与调试使用。
// 生产路径由 memory.Builder 负责拼装，避免两处逻辑漂移。
type PromptInput struct {
	Base           string
	Now            string
	MemoryDoc      string
	Summary        string
	WorkspaceFiles []string
}

// AssemblePrompt 按需拼装动态 System Prompt。
//
// 与 memory.Builder.assemblePrompt 保持一致的核心原则：
// 空记忆、空摘要、空工作区一律不注入，不给新会话增加任何额外开销。
func AssemblePrompt(in PromptInput) string {
	var sb strings.Builder

	base := in.Base
	if strings.TrimSpace(base) == "" {
		base = BasePrompt()
	}
	sb.WriteString(strings.TrimSpace(base))

	if in.Now != "" {
		sb.WriteString("\n\n## 当前日期\n\n")
		sb.WriteString(in.Now)
	}

	if strings.TrimSpace(in.MemoryDoc) != "" {
		sb.WriteString("\n\n## 关于这位学生\n\n")
		sb.WriteString(strings.TrimSpace(in.MemoryDoc))
	}

	if strings.TrimSpace(in.Summary) != "" {
		sb.WriteString("\n\n## 会话摘要\n\n")
		sb.WriteString(strings.TrimSpace(in.Summary))
	}

	if len(in.WorkspaceFiles) > 0 {
		sb.WriteString("\n\n## 工作区文件\n\n")
		sb.WriteString("当前工作区已有以下文件，可直接用文件工具读取：\n")
		for _, f := range in.WorkspaceFiles {
			sb.WriteString("- /workspace/")
			sb.WriteString(f)
			sb.WriteString("\n")
		}
	}

	return sb.String()
}
