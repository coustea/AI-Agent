package tui

import (
	"context"

	"my-agent/internal/agent"
	"my-agent/internal/gateway"
)

// AgentBridge 定义 TUI 前端与智能体内核的解耦契约接口
// TUI 仅依赖此流式接口，完全不关心具体是哪家网关或 SDK
type AgentBridge interface {
	// StreamRun 开启一个流式对话通道
	StreamRun(ctx context.Context, prompt string) (<-chan agent.AgentEvent, error)

	// Reset 清除会话历史上下文
	Reset()

	// SetGateway 运行时无损热切换底层大模型网关
	SetGateway(gw gateway.Gateway)
}
