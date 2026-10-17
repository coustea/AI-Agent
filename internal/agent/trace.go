package agent

import (
	"context"
	"time"

	"my-agent/internal/protocol"
)

// ============================================================================
// Agent 生命周期切面钩子与追踪数据契约 (零侵入可观测性中间件)
// ============================================================================

// LLMRequestTrace 记录向大模型发送的完整请求快照
type LLMRequestTrace struct {
	Step         int                       // 当前 ReAct 迭代步数 (0-indexed)
	Provider     string                    // 当前模型提供商 (如 deepseek, gemini)
	ModelName    string                    // 当前模型规格名称 (如 deepseek-reasoner)
	SystemPrompt string                    // 本轮合成的完整 System Prompt
	Messages     []protocol.Message        // 包含历史与当前提问的完整上下文切片
	Tools        []protocol.ToolDefinition // 注入大模型的工具能力元定义
	Timestamp    time.Time                 // 请求发起时间
}

// LLMResponseTrace 记录大模型返回的完整决策快照
type LLMResponseTrace struct {
	Step             int                 // 当前 ReAct 迭代步数
	Duration         time.Duration       // 大模型流式耗时
	Reply            string              // 大模型返回的正文内容 (Markdown)
	ReasoningContent string              // 深度思考链内容 (DeepSeek Reasoner 等返回的 CoT)
	ToolCalls        []protocol.ToolCall // 大模型要求执行的工具调用列表
	Usage            *protocol.Usage     // 本次交互消耗的 Token (Prompt/Completion)
	Error            error               // 若发生网络或模型异常则记录
}

// ToolTrace 记录工具执行前后的完整快照
type ToolTrace struct {
	Step      int                 // 所属 ReAct 步骤
	Call      protocol.ToolCall   // 工具调用定义 (ID, Name, Arguments)
	Result    protocol.ToolResult // 工具执行返回值与错误标记
	Duration  time.Duration       // 工具调用耗时
	Timestamp time.Time           // 执行时间
}

// TurnSummaryTrace 记录一轮完整问答的汇总快照
type TurnSummaryTrace struct {
	TurnID     string         // 对话轮次唯一标识符 (如 turn_1713345678)
	Prompt     string         // 用户原始提问
	TotalSteps int            // 本轮共经历的 ReAct 循环迭代次数
	TotalUsage protocol.Usage // 本轮累计消耗的总 Token
	Duration   time.Duration  // 从提问到收敛的总耗时
	Success    bool           // 是否成功完成
	Error      error          // 异常信息 (若有)
}

// AgentHook 定义智能体生命周期横切切面。
// 遵循 Hook / Middleware 思想：任何日志、耗时统计、审计等横切逻辑均通过挂载此接口实现，核心循环零侵入。
type AgentHook interface {
	// OnTurnStart 单轮交互开始
	OnTurnStart(ctx context.Context, turnID string, prompt string)

	// OnLLMRequest 每步发起大模型调用前
	OnLLMRequest(ctx context.Context, req *LLMRequestTrace)

	// OnLLMResponse 大模型决策返回完毕后
	OnLLMResponse(ctx context.Context, resp *LLMResponseTrace)

	// OnToolStart 工具调用开始前
	OnToolStart(ctx context.Context, step int, call protocol.ToolCall)

	// OnToolEnd 工具调用执行完毕后
	OnToolEnd(ctx context.Context, trace *ToolTrace)

	// OnTurnEnd 单轮交互完整收敛结束
	OnTurnEnd(ctx context.Context, summary *TurnSummaryTrace)
}
