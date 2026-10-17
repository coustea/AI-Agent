package agent

import (
	"context"

	"my-agent/internal/protocol"
)

// AgentHook 定义智能体生命周期横切切面。
// 遵循 Hook / Middleware 思想：任何日志、耗时统计、审计等横切逻辑均通过挂载此接口实现，核心循环零侵入。
type AgentHook interface {
	// OnTurnStart 单轮交互开始
	OnTurnStart(ctx context.Context, turnID string, prompt string)

	// OnLLMRequest 每步发起大模型调用前
	OnLLMRequest(ctx context.Context, req *protocol.LLMRequestTrace)

	// OnLLMResponse 大模型决策返回完毕后
	OnLLMResponse(ctx context.Context, resp *protocol.LLMResponseTrace)

	// OnToolStart 工具调用开始前
	OnToolStart(ctx context.Context, step int, call protocol.ToolCall)

	// OnToolEnd 工具调用执行完毕后
	OnToolEnd(ctx context.Context, trace *protocol.ToolTrace)

	// OnTurnEnd 单轮交互完整收敛结束
	OnTurnEnd(ctx context.Context, summary *protocol.TurnSummaryTrace)
}

func (a *CoreAgent) dispatchTurnStart(ctx context.Context, turnID string, prompt string) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnTurnStart(ctx, turnID, prompt)
	}
}

func (a *CoreAgent) dispatchLLMRequest(ctx context.Context, req *protocol.LLMRequestTrace) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnLLMRequest(ctx, req)
	}
}

func (a *CoreAgent) dispatchLLMResponse(ctx context.Context, resp *protocol.LLMResponseTrace) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnLLMResponse(ctx, resp)
	}
}

func (a *CoreAgent) dispatchToolStart(ctx context.Context, step int, call protocol.ToolCall) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnToolStart(ctx, step, call)
	}
}

func (a *CoreAgent) dispatchToolEnd(ctx context.Context, trace *protocol.ToolTrace) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnToolEnd(ctx, trace)
	}
}

func (a *CoreAgent) dispatchTurnEnd(ctx context.Context, summary *protocol.TurnSummaryTrace) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnTurnEnd(ctx, summary)
	}
}
