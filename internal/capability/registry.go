// Package capability 管理 Agent 可用的能力（工具）。
//
// 为什么需要它：能力是 Agent 系统的扩展点。旧实现里工具在 router 里硬编码，
// 再作为可变参数传给 builder——每加一个工具就要改三处（构造、传参、装配），
// 而且无法按环境开关。这里把「有哪些能力」变成一份可声明的注册表。
//
// 设计原则：
//   - 注册表在启动时一次性组装完成，运行期只读，无并发问题；
//   - 每个能力自带启用条件（例如未配置记忆就不注册 remember），
//     避免调用方到处写 nil 判断；
//   - 能力只依赖自己需要的最小接口，不感知编排层。
package capability

import (
	"context"

	"github.com/cloudwego/eino/components/tool"

	"mentorly/internal/agent"
	"mentorly/internal/memory"
)

// Registry 是本轮可用的工具集合。
type Registry struct {
	tools []tool.BaseTool
}

// NewRegistry 从能力声明组装注册表。
// 每一项为 nil 或未启用时自动跳过，调用方无需过滤。
func NewRegistry(items ...tool.BaseTool) *Registry {
	tools := make([]tool.BaseTool, 0, len(items))
	for _, t := range items {
		if t != nil {
			tools = append(tools, t)
		}
	}
	return &Registry{tools: tools}
}

// Tools 返回已启用的工具，供 agent.Builder 装配。
func (r *Registry) Tools() []tool.BaseTool {
	if r == nil {
		return nil
	}
	return r.tools
}

// Len 返回已启用的能力数量，便于启动日志。
func (r *Registry) Len() int {
	if r == nil {
		return 0
	}
	return len(r.tools)
}

// Names 返回已启用能力的名称，用于启动期日志与排障。
func (r *Registry) Names() []string {
	if r == nil {
		return nil
	}
	out := make([]string, 0, len(r.tools))
	for _, t := range r.tools {
		if info, err := t.Info(context.Background()); err == nil && info != nil {
			out = append(out, info.Name)
		}
	}
	return out
}

// Memory 声明长期记忆能力。
//
// recorder 为 nil 时不启用（未配置记忆的环境）。
// 返回 nil 表示该能力不可用，NewRegistry 会自动跳过。
func Memory(recorder memory.Recorder) tool.BaseTool {
	if recorder == nil {
		return nil
	}
	return agent.NewRememberTool(recorder)
}
