// Package runtime 提供多个 Agent 与 Capability 共享的运行期能力：
// 请求身份上下文、模型装配、Eino Callback 观测与异步任务执行。
//
// 本包不包含任何 Agent 决策逻辑，也不认识 Tutor 的业务概念。
package runtime

import (
	"context"
	"strings"
	"sync"
)

// Principal 是一次 Agent 运行的身份与目录边界。
//
// Harness 在运行前创建它并注入 context；所有 Capability 的 Tool 只能
// 从这里取用户身份，绝不信任模型生成的参数。这是全部用户级隔离的唯一来源。
type Principal struct {
	// UserID 已认证用户，非空即有效
	UserID string
	// ConversationID 本次会话
	ConversationID string
	// Workspace 本次运行 /workspace 对应的宿主机目录
	Workspace string
	// Offload /offload 对应的宿主机目录
	Offload string
	// ArtifactDir 本次运行产物目录（宿主机路径）
	ArtifactDir string
	// Vision 当前模型是否支持图片原生输入
	Vision bool
}

// principalKey 是 context 私有键类型，避免与其他包冲突。
type principalKey struct{}

// WithPrincipal 把身份写入 context。
func WithPrincipal(ctx context.Context, p *Principal) context.Context {
	return context.WithValue(ctx, principalKey{}, p)
}

// PrincipalFrom 读取当前运行身份。
// 第二个返回值为 false 表示调用链上没有身份，Tool 必须据此拒绝执行。
func PrincipalFrom(ctx context.Context) (*Principal, bool) {
	p, ok := ctx.Value(principalKey{}).(*Principal)
	if !ok || p == nil || strings.TrimSpace(p.UserID) == "" {
		return nil, false
	}
	return p, true
}

// MustPrincipal 取身份，缺失时返回统一错误。
// Tool 的第一行都应该调用它，避免出现「忘记校验」的路径。
func MustPrincipal(ctx context.Context) (*Principal, error) {
	p, ok := PrincipalFrom(ctx)
	if !ok {
		return nil, ErrNoPrincipal
	}
	return p, nil
}

// runStateKey 是单次运行的计数器键。
type runStateKey struct{}

// RunState 保存单次运行的工具调用计数。
//
// 每个请求创建新实例并注入 context，绝不跨请求共享：
// 用全局 map 保存会话状态会在并发下互相污染，也会造成内存泄漏。
type RunState struct {
	mu        sync.Mutex
	toolCalls map[string]int
}

// NewRunState 创建一次运行的状态。
func NewRunState() *RunState {
	return &RunState{toolCalls: make(map[string]int)}
}

// WithRunState 把运行状态注入 context。
func WithRunState(ctx context.Context, s *RunState) context.Context {
	return context.WithValue(ctx, runStateKey{}, s)
}

// CountToolCall 把某个工具的调用计数加一并返回加之前的次数。
// 没有运行状态时返回 0，调用方据此放行（计数只是配额保护，不是权限）。
func CountToolCall(ctx context.Context, name string) int {
	s, ok := ctx.Value(runStateKey{}).(*RunState)
	if !ok || s == nil {
		return 0
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	n := s.toolCalls[name]
	s.toolCalls[name]++
	return n
}
