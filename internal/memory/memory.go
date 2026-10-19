package memory

import (
	"context"

	"my-agent/pkg/llm"
)

// Memory 定义 Agent 会话历史与上下文记忆管理的统一接口。
type Memory interface {
	// Append 追加单条对话消息（RoleUser, RoleAssistant, RoleTool）
	Append(ctx context.Context, msg llm.Message) error

	// BuildContext 根据系统提示与裁剪策略构建发往大模型的合法上下文消息序列
	BuildContext(ctx context.Context, systemPrompt string) ([]llm.Message, error)

	// History 返回当前保存的全部会话历史消息快照副本
	History() []llm.Message

	// Clear 清空当前会话记忆
	Clear()
}
