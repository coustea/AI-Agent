// Package agent 负责按轮创建无状态 eino ADK Agent 并消费其流式输出。
//
// 边界：本包不碰数据库、Redis、Gin 与网络传输格式。
// 它只接收「已经组装好的 Instruction、工作目录、工具」，因此可以脱离外部依赖被完整测试。
package chat

import (
	"context"
	_ "embed"
	"strings"
	"time"
)

//go:embed prompts/tutor.md
var tutorPrompt string

// BasePrompt 返回静态 System Prompt 底座。
// 动态段落（记忆、摘要、工作区索引）由 AssemblePrompt 追加。
func BasePrompt() string {
	return strings.TrimSpace(tutorPrompt)
}

// PromptInput 是动态 System Prompt 的拼装入参。
type PromptInput struct {
	// Base 静态底座，留空则用 BasePrompt()
	Base string
	// Now 当前日期，留空则不注入日期段
	Now string
	// Summary 会话摘要
	Summary string
	// WorkspaceFiles 工作区文件索引
	WorkspaceFiles []string
}

// AssemblePrompt 按需拼装动态 System Prompt。
//
// 核心原则（Zero Empty Noise）：任何一段没有内容就不注入，
// 未压缩过的新会话不会因此多付 token。
//
// 这是全系统唯一的 Prompt 拼装实现。
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

// BuildPrompt 是生产路径的便捷封装：注入当前日期再拼装。
func BuildPrompt(base, summary string, files []string) string {
	return AssemblePrompt(PromptInput{
		Base:           base,
		Now:            time.Now().Format("2006-01-02"),
		Summary:        summary,
		WorkspaceFiles: files,
	})
}

// scopeKey 是 Scope 在 context 中的私有键类型，避免与其他包冲突。
type scopeKey struct{}

// Scope 是本轮执行的目录与身份边界。
// 由编排层在调用 Agent 前放入 context，Sandbox 与工具都从这里取。
type Scope struct {
	// UserID 当前用户
	UserID string
	// SessionID 当前会话
	SessionID string
	// Root 会话工作目录在宿主机上的路径，对应 Agent 视角的 /workspace
	Root string
}

// WithScope 把 Scope 放入 context。
func WithScope(ctx context.Context, s Scope) context.Context {
	return context.WithValue(ctx, scopeKey{}, s)
}

// ScopeFrom 从 context 取出 Scope。
func ScopeFrom(ctx context.Context) (Scope, bool) {
	s, ok := ctx.Value(scopeKey{}).(Scope)
	return s, ok
}
