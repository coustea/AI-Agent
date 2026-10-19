package agent

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"my-agent/internal/protocol"
	"my-agent/pkg/llm"
)

// Run 严格实现 protocol.Agent 契约，负责轮次生命周期、并发互斥与事件通道管理
func (a *CoreAgent) Run(ctx context.Context, prompt string) (<-chan protocol.Event, error) {
	prompt = strings.TrimSpace(prompt)
	if prompt == "" {
		return nil, ErrEmptyPrompt
	}

	if ctx == nil {
		ctx = context.Background()
	}

	a.mu.RLock()
	llmClient := a.llm
	a.mu.RUnlock()
	if llmClient == nil {
		return nil, errors.New("agent: no LLM client configured, please configure via /model")
	}

	a.mu.Lock()
	if a.running {
		a.mu.Unlock()
		return nil, ErrRunInProgress
	}
	a.running = true
	a.mu.Unlock()

	outCh := make(chan protocol.Event, 32)

	go func() {
		defer close(outCh)
		defer func() {
			// panic 兜底：agentLoop 崩溃时保证 running 复位与通道正常关闭，整轮以 EventError 收敛
			if r := recover(); r != nil {
				sendEvent(context.Background(), outCh, protocol.Event{
					Type:  protocol.EventError,
					Error: fmt.Sprintf("agent: internal panic: %v", r),
				})
			}
			a.mu.Lock()
			a.running = false
			a.mu.Unlock()
		}()

		a.agentLoop(ctx, prompt, outCh)
	}()

	return outCh, nil
}

// agentLoop 是驱动 Agent 运转的核心循环：负责单轮生命周期追踪、用户输入归档、动态提示词组装与 ReAct 状态机推进
func (a *CoreAgent) agentLoop(ctx context.Context, prompt string, eventCh chan<- protocol.Event) {
	// 1. 将事件通道装载入 context，供装配期挂载的横切钩子（如权限交互审批桥）回传事件
	ctx = withEventSink(ctx, eventCh)

	turnID := fmt.Sprintf("turn_%d", time.Now().UnixNano())
	turnStart := time.Now()
	a.dispatchTurnStart(ctx, turnID, prompt)

	var (
		totalTurnUsage llm.Usage
		turnErr        error
		stepCount      int
	)

	defer func() {
		a.dispatchTurnEnd(ctx, &protocol.TurnSummaryTrace{
			TurnID:     turnID,
			Prompt:     prompt,
			TotalSteps: stepCount,
			TotalUsage: totalTurnUsage,
			Duration:   time.Since(turnStart),
			Success:    turnErr == nil,
			Error:      turnErr,
		})
	}()

	// 2. 将用户问题存入 Memory
	userMsg := llm.Message{Role: llm.RoleUser, Content: prompt}
	_ = a.memory.Append(ctx, userMsg)

	// 3. 每用户轮次开始时动态合成系统提示词
	a.mu.RLock()
	sysPrompt := composeSystemPrompt(a.persona, a.workDir)
	a.mu.RUnlock()

	// 4. 驱动 ReAct 循环 (最多迭代 maxSteps 步)
	for step := 0; step < a.maxSteps; step++ {
		stepCount = step + 1
		select {
		case <-ctx.Done():
			turnErr = ctx.Err()
			sendEvent(ctx, eventCh, protocol.Event{Type: protocol.EventError, Error: ctx.Err().Error()})
			return
		default:
		}

		stepUsage, finished, err := a.executeStep(ctx, eventCh, sysPrompt, step)
		if err != nil {
			turnErr = err
			sendEvent(ctx, eventCh, protocol.Event{Type: protocol.EventError, Error: err.Error()})
			return
		}
		totalTurnUsage.Add(stepUsage)
		if finished {
			sendEvent(ctx, eventCh, protocol.Event{
				Type:  protocol.EventDone,
				Usage: &totalTurnUsage,
			})
			return
		}
	}

	turnErr = ErrMaxSteps
	sendEvent(ctx, eventCh, protocol.Event{
		Type:  protocol.EventError,
		Error: ErrMaxSteps.Error(),
	})
}

// executeStep 执行单步 ReAct：调用一次流式大模型，解析思考过程与文本内容，并在有工具调用时驱动工具流水线。
// 返回本步 token 用量；finished 为 true 表示模型已给出最终答复，无需继续迭代。
func (a *CoreAgent) executeStep(ctx context.Context, eventCh chan<- protocol.Event, sysPrompt string, step int) (stepUsage llm.Usage, finished bool, err error) {
	a.mu.RLock()
	var providerName, modelName string
	if a.cfg != nil {
		providerName = string(a.cfg.Provider)
		modelName = a.cfg.ModelName
	}
	llmClient := a.llm
	toolDefs := a.tools.Definitions()
	a.mu.RUnlock()
	if llmClient == nil {
		return stepUsage, false, errors.New("agent: no LLM client configured, please configure via /model")
	}

	// 基于记忆状态机安全构建当前上下文
	reqMsgs, err := a.memory.BuildContext(ctx, sysPrompt)
	if err != nil {
		return stepUsage, false, err
	}

	// 触发 OnLLMRequest 钩子
	stepStart := time.Now()
	a.dispatchLLMRequest(ctx, &protocol.LLMRequestTrace{
		Step:         step,
		Provider:     providerName,
		ModelName:    modelName,
		SystemPrompt: sysPrompt,
		Messages:     reqMsgs,
		Tools:        toolDefs,
		Timestamp:    stepStart,
	})

	// 发起大模型流式调用
	stream, err := llmClient.ChatStream(ctx, &llm.ChatRequest{
		Messages: reqMsgs,
		Tools:    toolDefs,
	})
	if err != nil {
		a.dispatchLLMResponse(ctx, &protocol.LLMResponseTrace{
			Step:     step,
			Duration: time.Since(stepStart),
			Error:    err,
		})
		return stepUsage, false, err
	}

	var replyBuilder, reasoningBuilder strings.Builder
	var toolCalls []llm.ToolCall
	for chunk := range stream {
		if chunk.Err != nil {
			// 流式异常回滚：本步 assistant 消息不入记忆
			a.dispatchLLMResponse(ctx, &protocol.LLMResponseTrace{
				Step:     step,
				Duration: time.Since(stepStart),
				Error:    chunk.Err,
			})
			return stepUsage, false, chunk.Err
		}
		if chunk.ReasoningContent != "" {
			reasoningBuilder.WriteString(chunk.ReasoningContent)
			sendEvent(ctx, eventCh, protocol.Event{
				Type:      protocol.EventReasoningDelta,
				Reasoning: chunk.ReasoningContent,
			})
		}
		if chunk.Delta != "" {
			replyBuilder.WriteString(chunk.Delta)
			sendEvent(ctx, eventCh, protocol.Event{
				Type:  protocol.EventDelta,
				Delta: chunk.Delta,
			})
		}
		if len(chunk.ToolCalls) > 0 {
			toolCalls = append(toolCalls, chunk.ToolCalls...)
		}
		if chunk.Done && chunk.Usage != nil {
			stepUsage.Add(*chunk.Usage)
		}
	}

	// 触发 OnLLMResponse 钩子
	a.dispatchLLMResponse(ctx, &protocol.LLMResponseTrace{
		Step:             step,
		Duration:         time.Since(stepStart),
		Reply:            replyBuilder.String(),
		ReasoningContent: reasoningBuilder.String(),
		ToolCalls:        toolCalls,
		Usage:            &stepUsage,
	})

	// 将模型本轮完整回复存入记忆
	_ = a.memory.Append(ctx, llm.Message{
		Role:             llm.RoleAssistant,
		Content:          replyBuilder.String(),
		ReasoningContent: reasoningBuilder.String(),
		ToolCalls:        toolCalls,
	})

	// 无工具调用：模型已得出最终回答
	if len(toolCalls) == 0 {
		return stepUsage, true, nil
	}

	// 执行工具调用流水线（权限、参数校验、大结果落盘均由 Registry 钩子自治完成）
	a.mu.RLock()
	tools := a.tools
	a.mu.RUnlock()
	for i, tc := range toolCalls {
		if ctx.Err() != nil {
			// 中途被取消时，为剩余全部未完成的 toolCalls 补齐取消状态，杜绝历史消息残缺导致后续 API 400
			for j := i; j < len(toolCalls); j++ {
				remTc := toolCalls[j]
				cancelRes := llm.ToolResult{
					ToolCallID: remTc.ID,
					Name:       remTc.Name,
					Content:    "[Execution cancelled by user]",
					IsError:    true,
				}
				_ = a.memory.Append(context.Background(), llm.Message{
					Role:       llm.RoleTool,
					ToolResult: &cancelRes,
				})
			}
			return stepUsage, false, ctx.Err()
		}

		a.dispatchToolStart(ctx, step, tc)

		if !sendEvent(ctx, eventCh, protocol.Event{
			Type:     protocol.EventToolCallStart,
			ToolCall: &tc,
		}) {
			for j := i; j < len(toolCalls); j++ {
				remTc := toolCalls[j]
				cancelRes := llm.ToolResult{
					ToolCallID: remTc.ID,
					Name:       remTc.Name,
					Content:    "[Execution cancelled by user]",
					IsError:    true,
				}
				_ = a.memory.Append(context.Background(), llm.Message{
					Role:       llm.RoleTool,
					ToolResult: &cancelRes,
				})
			}
			return stepUsage, false, ctx.Err()
		}

		toolStart := time.Now()
		res := tools.Execute(ctx, tc)
		toolDuration := time.Since(toolStart)

		a.dispatchToolEnd(ctx, &protocol.ToolTrace{
			Step:      step,
			Call:      tc,
			Result:    res,
			Duration:  toolDuration,
			Timestamp: toolStart,
		})

		_ = a.memory.Append(context.Background(), llm.Message{
			Role:       llm.RoleTool,
			ToolResult: &res,
		})

		if !sendEvent(ctx, eventCh, protocol.Event{
			Type:       protocol.EventToolCallResult,
			ToolResult: &res,
		}) {
			for j := i + 1; j < len(toolCalls); j++ {
				remTc := toolCalls[j]
				cancelRes := llm.ToolResult{
					ToolCallID: remTc.ID,
					Name:       remTc.Name,
					Content:    "[Execution cancelled by user]",
					IsError:    true,
				}
				_ = a.memory.Append(context.Background(), llm.Message{
					Role:       llm.RoleTool,
					ToolResult: &cancelRes,
				})
			}
			return stepUsage, false, ctx.Err()
		}
	}

	return stepUsage, false, nil
}

func sendEvent(ctx context.Context, eventCh chan<- protocol.Event, ev protocol.Event) bool {
	select {
	case eventCh <- ev:
		return true
	case <-ctx.Done():
		return false
	}
}
