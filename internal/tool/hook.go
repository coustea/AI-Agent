package tool

import (
	"context"

	"my-agent/internal/gateway"
)

// PreToolUse 是工具执行前的拦截钩子（对应 learn-claude-code 的 PreToolUse 事件）。
//
// 钩子在 Registry.Execute 的参数校验与工具执行之前被调用，按挂载顺序依次执行；
// 任一钩子返回非 nil 错误即短路，本次工具调用被阻止，错误内容作为观察结果回灌给模型。
//
// 设计要点：钩子只描述「策略」，不负责「执行」。Registry 自身不含任何策略，
// 只按序调用钩子——权限等横切能力因此是「挂载」在流水线上的，而不是嵌在循环或工具内部。
type PreToolUse func(ctx context.Context, call gateway.ToolCall) error
