package agent

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"sync"

	"my-agent/internal/config"
	"my-agent/internal/gateway"
	"my-agent/internal/memory"
	"my-agent/internal/permission"
	"my-agent/internal/protocol"
	"my-agent/internal/tool"
	"my-agent/internal/tool/builtin"
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
}

// Option 定义 Agent 的函数式拼装算子
type Option func(*CoreAgent)

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
	pendingMu    sync.Mutex
	pendingPerms map[string]chan protocol.Decision
	permSeq      uint64
}

// WithMemory 配置自定义记忆管理器
func WithMemory(m memory.Memory) Option {
	return func(a *CoreAgent) {
		if m != nil {
			a.memory = m
		}
	}
}

// WithTools 配置工具注册表
func WithTools(reg *tool.Registry) Option {
	return func(a *CoreAgent) {
		if reg != nil {
			a.tools = reg
		}
	}
}

// WithPermission 配置三道闸门权限管理器
func WithPermission(perm *permission.Manager) Option {
	return func(a *CoreAgent) {
		if perm != nil {
			a.permission = perm
		}
	}
}

// WithApprover 配置用户审批回调
func WithApprover(approver permission.Approver) Option {
	return func(a *CoreAgent) {
		if a.permission != nil {
			a.permission.SetApprover(approver)
		}
	}
}

// WithAutoApprove 配置是否自动放行非硬拒绝操作 (自动化测试或非交互模式使用)
func WithAutoApprove(auto bool) Option {
	return func(a *CoreAgent) {
		if a.permission != nil {
			a.permission.SetAutoApprove(auto)
		}
	}
}

// WithWorkDir 配置工作目录，并播种该工作区的记忆模板与刷新静态 persona
func WithWorkDir(dir string) Option {
	return func(a *CoreAgent) {
		cleanDir := strings.TrimSpace(dir)
		if cleanDir != "" {
			a.workDir = cleanDir
			_ = memory.InitTemplates(a.workDir)
			a.persona = defaultPersona(a.workDir)
			if a.permission != nil {
				a.permission.SetWorkDir(a.workDir)
			}
		}
	}
}

// WithDefaultTools 注册内置核心工具集，学习自 learn-claude-code (read_file, write_file, edit_file, glob, bash)
func WithDefaultTools(workDir ...string) Option {
	return func(a *CoreAgent) {
		wd := a.workDir
		if len(workDir) > 0 && strings.TrimSpace(workDir[0]) != "" {
			wd = strings.TrimSpace(workDir[0])
		}
		a.tools.Register(
			builtin.NewReadFileTool(wd),
			builtin.NewWriteFileTool(wd),
			builtin.NewEditFileTool(wd),
			builtin.NewGlobTool(wd),
			builtin.NewBashTool(wd),
		)
	}
}

// WithSystemPrompt 配置自定义 persona
func WithSystemPrompt(prompt string) Option {
	return func(a *CoreAgent) {
		if strings.TrimSpace(prompt) != "" {
			a.persona = strings.TrimSpace(prompt)
		}
	}
}

// WithMaxSteps 配置 ReAct 循环最大单轮迭代次数
func WithMaxSteps(steps int) Option {
	return func(a *CoreAgent) {
		if steps > 0 {
			a.maxSteps = steps
		}
	}
}

// WithConfig 配置初始配置对象与落盘路径
func WithConfig(cfg *config.Config, cfgPath ...string) Option {
	return func(a *CoreAgent) {
		a.cfg = cfg
		if len(cfgPath) > 0 && cfgPath[0] != "" {
			a.cfgPath = cfgPath[0]
		}
	}
}

// NewAgent 使用函数式选项构建 CoreAgent 实例；gw 为 nil 表示未就绪内核，
// 待 /model 向导补齐密钥后由 UpdateConfig 热装网关。
func NewAgent(gw gateway.Gateway, opts ...Option) (*CoreAgent, error) {
	wd, _ := os.Getwd()
	_ = memory.InitTemplates(wd)

	a := &CoreAgent{
		gw:           gw,
		workDir:      wd,
		memory:       memory.NewSlidingWindowMemory(40),
		tools:        tool.NewRegistry(),
		persona:      defaultPersona(wd),
		maxSteps:     10,
		pendingPerms: make(map[string]chan protocol.Decision),
	}

	// 默认装配权限管理器，将审批桥注入为默认 Approver
	a.permission = permission.NewManager(wd, permission.WithApprover(permission.ApproverFunc(a.bridgeApproval)))

	for _, opt := range opts {
		opt(a)
	}

	// 装配期在 tool.Registry 上挂载横切机制钩子（核心：机制挂上去，而不是嵌在循环里）
	a.tools.UsePreToolUse(a.permissionPreHook)
	a.tools.UsePostToolUse(a.largeResultPostHook)

	return a, nil
}

// NewFromConfig 根据配置一步初始化就绪的 CoreAgent（默认装配内置安全沙箱工具与配置自治管理）
func NewFromConfig(cfg *config.Config, opts ...Option) (*CoreAgent, error) {
	if cfg == nil {
		return nil, fmt.Errorf("agent: config cannot be nil")
	}
	gw, err := gateway.NewGatewayFromConfig(cfg)
	if err != nil && !errors.Is(err, gateway.ErrEmptyAPIKey) {
		return nil, err
	}
	// 远程厂商缺密钥：保留未就绪内核（gw 为 nil），待 /model 向导补齐后热装网关
	defaultOpts := []Option{
		WithDefaultTools(),
		WithConfig(cfg, config.DefaultConfigPath()),
	}
	defaultOpts = append(defaultOpts, opts...)
	return NewAgent(gw, defaultOpts...)
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

		// 2. 将用户问题存入 Memory
		userMsg := protocol.Message{Role: protocol.RoleUser, Content: prompt}
		_ = a.memory.Append(ctx, userMsg)

		// 3. 每用户轮次开始时动态合成系统提示词
		a.mu.RLock()
		sysPrompt := composeSystemPrompt(a.persona, a.workDir)
		a.mu.RUnlock()

		var totalTurnUsage protocol.Usage

		// 4. 驱动 Harness 循环 (最多迭代 maxSteps 步)
		for step := 0; step < a.maxSteps; step++ {
			select {
			case <-ctx.Done():
				sendEvent(ctx, outCh, protocol.Event{Type: protocol.EventError, Error: ctx.Err().Error()})
				return
			default:
			}

			stepUsage, finished, err := a.runStep(ctx, outCh, sysPrompt)
			if err != nil {
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

		sendEvent(ctx, outCh, protocol.Event{
			Type:  protocol.EventError,
			Error: ErrMaxSteps.Error(),
		})
	}()

	return outCh, nil
}

// runStep 执行单步 ReAct：一次流式模型调用，必要时执行其发起的工具调用。
// 返回本步 token 用量；finished 为 true 表示模型已给出最终答复，循环应终止。
func (a *CoreAgent) runStep(ctx context.Context, outCh chan<- protocol.Event, sysPrompt string) (protocol.Usage, bool, error) {
	var stepUsage protocol.Usage

	a.mu.RLock()
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

	// 发起网关流式调用
	stream, err := gw.ChatStream(ctx, &gateway.ChatRequest{
		Messages: reqMsgs,
		Tools:    toolDefs,
	})
	if err != nil {
		return stepUsage, false, err
	}

	var replyBuilder, reasoningBuilder strings.Builder
	var toolCalls []protocol.ToolCall
	for chunk := range stream {
		if chunk.Err != nil {
			// 流式异常回滚：本步 assistant 消息不入记忆
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
		sendEvent(ctx, outCh, protocol.Event{
			Type:     protocol.EventToolCallStart,
			ToolCall: &tc,
		})

		res := tools.Execute(ctx, tc)

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

func sendEvent(ctx context.Context, ch chan<- protocol.Event, ev protocol.Event) bool {
	select {
	case ch <- ev:
		return true
	case <-ctx.Done():
		return false
	}
}
