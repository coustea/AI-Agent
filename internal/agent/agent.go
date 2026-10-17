package agent

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"

	"my-agent/internal/config"
	"my-agent/internal/gateway"
	"my-agent/internal/memory"
	"my-agent/internal/permission"
	"my-agent/internal/protocol"
	"my-agent/internal/tool"
)

var (
	ErrEmptyPrompt   = errors.New("agent: prompt cannot be empty")
	ErrRunInProgress = errors.New("agent: another turn is already running")
	ErrMaxSteps      = errors.New("agent: exceeded maximum ReAct steps")
)

// Agent 定义智能体调用的对外核心契约，任何前端（TUI、桌面端、无头宿主）直接引入使用
type Agent interface {
	// StreamRun 开启单轮对话交互，返回原生支持序列化的纯数据事件流
	StreamRun(ctx context.Context, prompt string) (<-chan protocol.Event, error)

	// RespondPermission 异步审批权限请求（基于 requestID 关联）
	RespondPermission(requestID string, decision protocol.Decision) error

	// Reset 清空当前会话记忆
	Reset()

	// Config 获取当前配置与就绪状态（只读视图）
	Config() protocol.ConfigView

	// UpdateConfig 更新模型提供商、密钥与模型名称（内核负责落盘 config.json 与热切网关）
	UpdateConfig(provider, apiKey, model string) error

	// MemoryCount 返回当前工作区生效的长期记忆篇数
	MemoryCount() int

	// WorkDir 获取当前绑定的工作目录
	WorkDir() string

	// Traces 返回当前/最近一轮对话的完整详细结构化追踪事件切片
	Traces() []TraceEvent
}

// CoreAgent 是基于 Harness 思想驱动 ReAct 循环与状态机管理的运行核心
type CoreAgent struct {
	mu           sync.RWMutex
	gw           gateway.Gateway
	cfg          *config.Config
	cfgPath      string
	workDir      string
	memory       memory.Memory
	tools        *tool.Registry
	permission   *permission.Manager
	persona      string
	maxSteps     int
	running      bool
	hooks        []AgentHook
	pendingMu    sync.Mutex
	pendingPerms map[string]chan protocol.Decision
	permSeq      uint64
}

// Config 返回当前配置与就绪状态视图（由配置中心自主映射，内核只负责转发）
func (a *CoreAgent) Config() protocol.ConfigView {
	a.mu.RLock()
	defer a.mu.RUnlock()
	if a.cfg != nil {
		return a.cfg.ToView()
	}
	return config.DefaultConfig().ToView()
}

// UpdateConfig 运行时更新模型提供商、密钥与模型名称（由内核自动负责校验、落盘 config.json 与热切网关）
func (a *CoreAgent) UpdateConfig(provider, apiKey, model string) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	if a.cfg == nil {
		a.cfg = &config.Config{
			Provider:  config.ProviderLlamaCpp,
			ModelName: config.DefaultLlamaCppModel,
			BaseURL:   config.DefaultLlamaCppBaseURL,
		}
	}

	// 1. 若未显式传入 provider，尝试从 model 名称智能识别所属厂商或保持当前激活厂商
	pStr := strings.TrimSpace(provider)
	mStr := strings.TrimSpace(model)
	if pStr == "" && mStr != "" {
		if inferred := config.InferProviderFromModel(mStr); inferred != "" {
			pStr = string(inferred)
		}
	}
	if pStr == "" {
		pStr = string(a.cfg.Provider)
	}

	newProvider := config.Provider(pStr)
	// 切换厂商（自动载入该厂商已保存的配置历史）
	a.cfg.SwitchProvider(newProvider)

	// 2. 检查并更新 APIKey（若传入非空，则更新并覆盖；若传入空，则沿用该厂商已保存的密钥）
	if strings.TrimSpace(apiKey) != "" {
		a.cfg.APIKey = strings.TrimSpace(apiKey)
	}

	// 3. 检查并更新 ModelName
	if mStr != "" {
		a.cfg.ModelName = mStr
	} else if a.cfg.ModelName == "" {
		a.cfg.ModelName = config.DefaultModel(newProvider)
	}

	// 4. 远程厂商必须具备有效 APIKey
	if !config.IsLocalProvider(newProvider) && strings.TrimSpace(a.cfg.APIKey) == "" {
		return fmt.Errorf("agent: provider %q requires an API key", newProvider)
	}

	if a.cfgPath == "" {
		a.cfgPath = config.DefaultConfigPath()
	}
	if err := config.SaveConfig(a.cfgPath, a.cfg); err != nil {
		return fmt.Errorf("agent: save config failed: %w", err)
	}

	gw, err := gateway.NewGatewayFromConfig(a.cfg)
	if err != nil {
		return fmt.Errorf("agent: initialize gateway failed: %w", err)
	}
	a.gw = gw
	return nil
}

// RespondPermission 异步审批权限请求（无状态，由 RequestID 关联）
func (a *CoreAgent) RespondPermission(requestID string, decision protocol.Decision) error {
	a.pendingMu.Lock()
	ch, ok := a.pendingPerms[requestID]
	a.pendingMu.Unlock()
	if !ok {
		return fmt.Errorf("agent: permission request %q not found or already resolved", requestID)
	}
	select {
	case ch <- decision:
		return nil
	default:
		return fmt.Errorf("agent: permission request %q is busy or channel closed", requestID)
	}
}

// SetGateway 支持运行时热切换大模型网关
func (a *CoreAgent) SetGateway(gw gateway.Gateway) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if gw != nil {
		a.gw = gw
	}
}

// MemoryCount 返回当前工作区生效的长期记忆篇数，供前端直接展示
func (a *CoreAgent) MemoryCount() int {
	a.mu.RLock()
	wd := a.workDir
	a.mu.RUnlock()
	bundle := memory.LoadBundle(wd)
	return len(bundle.GlobalFiles) + len(bundle.ProjectFiles)
}

// Traces 返回当前/最近一轮对话由日志中间件捕获的全量结构化追踪事件
func (a *CoreAgent) Traces() []TraceEvent {
	a.mu.RLock()
	defer a.mu.RUnlock()
	for _, h := range a.hooks {
		if lm, ok := h.(*LoggingMiddleware); ok {
			return lm.Traces()
		}
	}
	return nil
}

// TotalUsage 获取当前实例累计消耗的总 Token 用量
func (a *CoreAgent) TotalUsage() protocol.Usage {
	a.mu.RLock()
	defer a.mu.RUnlock()
	if a.gw != nil {
		u := a.gw.TotalUsage()
		return protocol.Usage{
			PromptTokens:     u.PromptTokens,
			CompletionTokens: u.CompletionTokens,
			TotalTokens:      u.TotalTokens,
		}
	}
	return protocol.Usage{}
}

// Reset 清空当前会话记忆
func (a *CoreAgent) Reset() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.memory.Clear()
}

// History 获取历史消息快照（内部测试与监控使用）
func (a *CoreAgent) History() []protocol.Message {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.memory.History()
}

// SystemPrompt 获取当前由 persona 与长期记忆合成的完整系统提示词
func (a *CoreAgent) SystemPrompt() string {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return composeSystemPrompt(a.persona, a.workDir)
}

// WorkDir 获取当前绑定的工作目录
func (a *CoreAgent) WorkDir() string {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.workDir
}

// Permission 获取权限管理器实例
func (a *CoreAgent) Permission() *permission.Manager {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.permission
}

// RegisterTools 动态增加工具
func (a *CoreAgent) RegisterTools(ts ...tool.Tool) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.tools.Register(ts...)
}

// StreamRun 驱动 Harness 核心 ReAct 状态循环，返回纯数据事件流
func (a *CoreAgent) StreamRun(ctx context.Context, prompt string) (<-chan protocol.Event, error) {
	prompt = strings.TrimSpace(prompt)
	if prompt == "" {
		return nil, ErrEmptyPrompt
	}

	if ctx == nil {
		ctx = context.Background()
	}

	a.mu.RLock()
	gw := a.gw
	a.mu.RUnlock()
	if gw == nil {
		return nil, errors.New("agent: no model gateway configured, please configure via /model")
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
			a.mu.Lock()
			a.running = false
			a.mu.Unlock()
		}()

		// 1. 将事件通道装载入 context，供装配期挂载的横切钩子（如权限交互审批桥）回传事件
		ctx = withEventSink(ctx, outCh)

		turnID := fmt.Sprintf("turn_%d", time.Now().UnixNano())
		turnStart := time.Now()
		a.dispatchTurnStart(ctx, turnID, prompt)

		var (
			totalTurnUsage protocol.Usage
			turnErr        error
			stepCount      int
		)

		defer func() {
			a.dispatchTurnEnd(ctx, &TurnSummaryTrace{
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
		userMsg := protocol.Message{Role: protocol.RoleUser, Content: prompt}
		_ = a.memory.Append(ctx, userMsg)

		// 3. 每用户轮次开始时动态合成系统提示词
		a.mu.RLock()
		sysPrompt := composeSystemPrompt(a.persona, a.workDir)
		a.mu.RUnlock()

		// 4. 驱动 Harness 循环 (最多迭代 maxSteps 步)
		for step := 0; step < a.maxSteps; step++ {
			stepCount = step + 1
			select {
			case <-ctx.Done():
				turnErr = ctx.Err()
				sendEvent(ctx, outCh, protocol.Event{Type: protocol.EventError, Error: ctx.Err().Error()})
				return
			default:
			}

			stepUsage, finished, err := a.runStep(ctx, outCh, sysPrompt, step)
			if err != nil {
				turnErr = err
				sendEvent(ctx, outCh, protocol.Event{Type: protocol.EventError, Error: err.Error()})
				return
			}
			totalTurnUsage.Add(stepUsage)
			if finished {
				sendEvent(ctx, outCh, protocol.Event{
					Type:  protocol.EventDone,
					Usage: &totalTurnUsage,
				})
				return
			}
		}

		turnErr = ErrMaxSteps
		sendEvent(ctx, outCh, protocol.Event{
			Type:  protocol.EventError,
			Error: ErrMaxSteps.Error(),
		})
	}()

	return outCh, nil
}

// runStep 执行单步 ReAct：一次流式模型调用，必要时执行其发起的工具调用。
// 返回本步 token 用量；finished 为 true 表示模型已给出最终答复，循环应终止。
func (a *CoreAgent) runStep(ctx context.Context, outCh chan<- protocol.Event, sysPrompt string, step int) (protocol.Usage, bool, error) {
	var stepUsage protocol.Usage

	a.mu.RLock()
	var providerName, modelName string
	if a.cfg != nil {
		providerName = string(a.cfg.Provider)
		modelName = a.cfg.ModelName
	}
	gw := a.gw
	toolDefs := a.tools.Definitions()
	a.mu.RUnlock()
	if gw == nil {
		return stepUsage, false, errors.New("agent: no model gateway configured, please configure via /model")
	}

	// 基于记忆状态机安全构建当前上下文
	reqMsgs, err := a.memory.BuildContext(ctx, sysPrompt)
	if err != nil {
		return stepUsage, false, err
	}

	// 触发 OnLLMRequest 钩子
	stepStart := time.Now()
	a.dispatchLLMRequest(ctx, &LLMRequestTrace{
		Step:         step,
		Provider:     providerName,
		ModelName:    modelName,
		SystemPrompt: sysPrompt,
		Messages:     reqMsgs,
		Tools:        toolDefs,
		Timestamp:    stepStart,
	})

	// 发起网关流式调用
	stream, err := gw.ChatStream(ctx, &protocol.ChatRequest{
		Messages: reqMsgs,
		Tools:    toolDefs,
	})
	if err != nil {
		a.dispatchLLMResponse(ctx, &LLMResponseTrace{
			Step:     step,
			Duration: time.Since(stepStart),
			Error:    err,
		})
		return stepUsage, false, err
	}

	var replyBuilder, reasoningBuilder strings.Builder
	var toolCalls []protocol.ToolCall
	for chunk := range stream {
		if chunk.Err != nil {
			// 流式异常回滚：本步 assistant 消息不入记忆
			a.dispatchLLMResponse(ctx, &LLMResponseTrace{
				Step:     step,
				Duration: time.Since(stepStart),
				Error:    chunk.Err,
			})
			return stepUsage, false, chunk.Err
		}
		if chunk.ReasoningContent != "" {
			reasoningBuilder.WriteString(chunk.ReasoningContent)
			sendEvent(ctx, outCh, protocol.Event{
				Type:      protocol.EventReasoningDelta,
				Reasoning: chunk.ReasoningContent,
			})
		}
		if chunk.Delta != "" {
			replyBuilder.WriteString(chunk.Delta)
			sendEvent(ctx, outCh, protocol.Event{
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
	a.dispatchLLMResponse(ctx, &LLMResponseTrace{
		Step:             step,
		Duration:         time.Since(stepStart),
		Reply:            replyBuilder.String(),
		ReasoningContent: reasoningBuilder.String(),
		ToolCalls:        toolCalls,
		Usage:            &stepUsage,
	})

	// 将模型本轮完整回复存入记忆
	_ = a.memory.Append(ctx, protocol.Message{
		Role:             protocol.RoleAssistant,
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
	for _, tc := range toolCalls {
		a.dispatchToolStart(ctx, step, tc)

		sendEvent(ctx, outCh, protocol.Event{
			Type:     protocol.EventToolCallStart,
			ToolCall: &tc,
		})

		toolStart := time.Now()
		res := tools.Execute(ctx, tc)
		toolDuration := time.Since(toolStart)

		a.dispatchToolEnd(ctx, &ToolTrace{
			Step:      step,
			Call:      tc,
			Result:    res,
			Duration:  toolDuration,
			Timestamp: toolStart,
		})

		sendEvent(ctx, outCh, protocol.Event{
			Type:       protocol.EventToolCallResult,
			ToolResult: &res,
		})

		_ = a.memory.Append(ctx, protocol.Message{
			Role:       protocol.RoleTool,
			ToolResult: &res,
		})
	}

	return stepUsage, false, nil
}

func (a *CoreAgent) dispatchTurnStart(ctx context.Context, turnID string, prompt string) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnTurnStart(ctx, turnID, prompt)
	}
}

func (a *CoreAgent) dispatchLLMRequest(ctx context.Context, req *LLMRequestTrace) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnLLMRequest(ctx, req)
	}
}

func (a *CoreAgent) dispatchLLMResponse(ctx context.Context, resp *LLMResponseTrace) {
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

func (a *CoreAgent) dispatchToolEnd(ctx context.Context, trace *ToolTrace) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnToolEnd(ctx, trace)
	}
}

func (a *CoreAgent) dispatchTurnEnd(ctx context.Context, summary *TurnSummaryTrace) {
	a.mu.RLock()
	hooks := a.hooks
	a.mu.RUnlock()
	for _, h := range hooks {
		h.OnTurnEnd(ctx, summary)
	}
}

func sendEvent(ctx context.Context, ch chan<- protocol.Event, ev protocol.Event) bool {
	select {
	case ch <- ev:
		return true
	case <-ctx.Done():
		return false
	}
}
