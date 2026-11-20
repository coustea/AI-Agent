// Package agent 负责按轮创建无状态 eino ADK Agent 并消费其流式输出。
//
// 边界：本包不碰数据库、Redis 与 Gin。它只接收「已经组装好的 Instruction、
// 工作目录、工具与记忆追加器」，因此可以脱离外部依赖被完整测试。
package agent

import "context"

// scopeKey 是 Scope 在 context 中的私有键类型，避免与其他包冲突。
type scopeKey struct{}

// Scope 是本轮执行的目录与身份边界。
// 由 Harness 在调用 Agent 前放入 context，Sandbox 与工具都从这里取。
type Scope struct {
	// UserID 当前用户
	UserID string
	// SessionID 当前会话
	SessionID string
	// Root 会话工作目录在宿主机上的绝对或相对路径
	// 对应 Agent 视角的 /workspace
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
