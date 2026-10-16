package agent

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"sync"
	"sync/atomic"

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
	ErrNilGateway    = errors.New("agent: gateway client cannot be nil")
	ErrRunInProgress = errors.New("agent: another turn is already running")
	ErrMaxSteps      = errors.New("agent: exceeded maximum ReAct steps")
)

// defaultPersona 构建 coustea 的静态身份与行为准则（不含长期记忆）。
// 长期记忆由 composeSystemPrompt 在每轮对话开始时动态注入，保证运行期沉淀即时生效。
func defaultPersona(workDir string) string {
	workDir = strings.TrimSpace(workDir)
	if workDir == "" {
		if wd, err := os.Getwd(); err == nil {
			workDir = wd
		}
	}

	var sb strings.Builder
	sb.WriteString("You are coustea, an intelligent and versatile general-purpose local AI personal assistant.\n")
	sb.WriteString("You run directly on the user's local machine with native capabilities, helping with a wide range of tasks including reasoning, analysis, research, coding, file management, system operations, writing, and daily workflows.\n")
	if workDir != "" {
		sb.WriteString(fmt.Sprintf("Working Directory: %s\n", workDir))
	}

	sb.WriteString("\nAutonomous Problem-Solving Mindset:\n")
	sb.WriteString("- Be a proactive agent, not a passive text predictor. You have real tools and can interact with the environment to solve problems end-to-end.\n")
	sb.WriteString("- Never claim 'I cannot access real-time information', 'I don't know', or 'I cannot perform this' without first checking if your tools can accomplish it.\n")
	sb.WriteString("- When faced with questions involving external state, real-time data, network queries, system status, or file contents, proactively use available tools to discover the facts before responding.\n")
	sb.WriteString("- Reason before acting (ReAct): clearly identify the goal, formulate an actionable plan, call appropriate tools, observe the results, and iteratively solve the problem until completion.\n")

	sb.WriteString("\nTool Usage Principles:\n")
	sb.WriteString("- bash: Use for executing non-interactive CLI commands, system diagnostics, running code/tests, git operations, and querying public web endpoints or APIs via utilities like curl.\n")
	sb.WriteString("- read_file & glob: Use glob to locate files across project directories, and read_file to examine code or configuration before making any assumptions or modifications.\n")
	sb.WriteString("- edit_file & write_file: Prefer edit_file for precise, surgical replacements in existing files; use write_file when creating new files or when a complete rewrite is necessary.\n")
	sb.WriteString("- Safety & Permissions: Destructive commands or modifications outside the working directory will be reviewed via the permission pipeline. Be judicious, safe, and transparent.\n")

	sb.WriteString("\nCommunication Style:\n")
	sb.WriteString("- Communicate clearly, concisely, and directly, defaulting to Chinese unless the user asks otherwise.\n")
	sb.WriteString("- Focus on delivering actionable solutions, insights, and verifiable outcomes rather than unnecessary filler or disclaimers.\n")

	return sb.String()
}

// composeSystemPrompt 将静态 persona 与实时读取的长期记忆合成为最终系统提示词。
func composeSystemPrompt(persona, workDir string) string {
	memoryBlock := memory.LoadBundle(workDir).FormatForPrompt()
	if memoryBlock == "" {
		return persona
	}
	return persona + "\n\n" + memoryBlock
}

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

	// TotalUsage 获取当前实例累计消耗的总 Token 用量
	TotalUsage() protocol.Usage

	// SystemPrompt 获取当前由 persona 与长期记忆合成的完整系统提示词
	SystemPrompt() string

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
				a.permission = permission.NewManager(a.workDir, permission.WithApprover(a.permission.Approver()))
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

// NewAgent 使用函数式选项构建 CoreAgent 实例（严格遵守零 nil 默认装配原则）
func NewAgent(gw gateway.Gateway, opts ...Option) (*CoreAgent, error) {
	if gw == nil {
		return nil, ErrNilGateway
	}

	wd, _ := os.Getwd()
	_ = memory.InitTemplates(wd)

	a := &CoreAgent{
		gw:           gw,
		workDir:      wd,
		memory:       memory.NewSlidingWindowMemory(40),
		tools:        tool.NewRegistry(),
		permission:   permission.NewManager(wd),
		persona:      defaultPersona(wd),
		maxSteps:     10,
		pendingPerms: make(map[string]chan protocol.Decision),
	}

	for _, opt := range opts {
		opt(a)
	}

	return a, nil
}

// NewFromConfig 根据配置一步初始化就绪的 CoreAgent（默认装配内置安全沙箱工具与配置自治管理）
func NewFromConfig(cfg *config.Config, opts ...Option) (*CoreAgent, error) {
	if cfg == nil {
		return nil, fmt.Errorf("agent: config cannot be nil")
	}
	gw, err := gateway.NewGatewayFromConfig(cfg)
	if err != nil {
		return nil, err
	}
	defaultOpts := []Option{
		WithDefaultTools(),
		WithConfig(cfg, config.DefaultConfigPath()),
	}
	defaultOpts = append(defaultOpts, opts...)
	return NewAgent(gw, defaultOpts...)
}

// Config 返回当前配置与就绪状态视图（只读数据，供 UI 呈现）
func (a *CoreAgent) Config() protocol.ConfigView {
	a.mu.RLock()
	defer a.mu.RUnlock()

	available := []string{
		string(config.ProviderLlamaCpp),
		string(config.ProviderDeepSeek),
		string(config.ProviderGemini),
		string(config.ProviderSpark),
	}

	cv := protocol.ConfigView{
		AvailableProviders: available,
	}
	if a.cfg != nil {
		cv.Provider = string(a.cfg.Provider)
		cv.ModelName = a.cfg.ModelName
		cv.HasAPIKey = a.cfg.APIKey != "" || config.IsLocalProvider(a.cfg.Provider)
	}

	providers := make([]protocol.ProviderInfo, 0, len(available))
	for _, pStr := range available {
		p := config.Provider(pStr)
		info := protocol.ProviderInfo{
			ID:                pStr,
			Name:              config.ProviderDisplayName(p),
			Description:       config.ProviderDescription(p),
			IsLocal:           config.IsLocalProvider(p),
			RecommendedModels: config.RecommendedModels(p),
		}

		if a.cfg != nil {
			pcfg := a.cfg.ProviderConfig(p)
			if pcfg.ModelName != "" {
				info.CurrentModel = pcfg.ModelName
			} else {
				info.CurrentModel = config.DefaultModel(p)
			}

			if info.IsLocal {
				info.IsConfigured = true
			} else if pcfg.APIKey != "" {
				info.IsConfigured = true
			} else if a.cfg.Provider == p && a.cfg.APIKey != "" {
				info.IsConfigured = true
			}
		} else {
			info.CurrentModel = config.DefaultModel(p)
			info.IsConfigured = info.IsLocal
		}

		providers = append(providers, info)
	}
	cv.Providers = providers
	return cv
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
func (a *CoreAgent) History() []gateway.Message {
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

		// 1. 将用户问题存入 Memory
		userMsg := gateway.Message{Role: gateway.RoleUser, Content: prompt}
		_ = a.memory.Append(ctx, userMsg)

		// 2. 每用户轮次开始时动态合成系统提示词
		a.mu.RLock()
		sysPrompt := composeSystemPrompt(a.persona, a.workDir)
		permMgr := a.permission
		a.mu.RUnlock()

		var totalTurnUsage gateway.Usage

		// 3. 驱动 Harness 循环 (最多迭代 maxSteps 步)
		for step := 0; step < a.maxSteps; step++ {
			select {
			case <-ctx.Done():
				sendEvent(ctx, outCh, protocol.Event{Type: protocol.EventError, Error: ctx.Err().Error()})
				return
			default:
			}

			a.mu.RLock()
			gw := a.gw
			toolDefs := a.tools.Definitions()
			a.mu.RUnlock()

			// 基于记忆状态机安全构建当前上下文
			reqMsgs, err := a.memory.BuildContext(ctx, sysPrompt)
			if err != nil {
				sendEvent(ctx, outCh, protocol.Event{Type: protocol.EventError, Error: err.Error()})
				return
			}

			// 发起网关流式调用
			stream, err := gw.ChatStream(ctx, &gateway.ChatRequest{
				Messages: reqMsgs,
				Tools:    toolDefs,
			})
			if err != nil {
				sendEvent(ctx, outCh, protocol.Event{Type: protocol.EventError, Error: err.Error()})
				return
			}

			var replyBuilder strings.Builder
			var reasoningBuilder strings.Builder
			var toolCalls []gateway.ToolCall
			var streamErr error

			for chunk := range stream {
				if chunk.Err != nil {
					streamErr = chunk.Err
					break
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
					totalTurnUsage.Add(*chunk.Usage)
				}
			}

			// 流式异常回滚原则
			if streamErr != nil {
				sendEvent(ctx, outCh, protocol.Event{Type: protocol.EventError, Error: streamErr.Error()})
				return
			}

			// 将模型本轮完整回复存入记忆
			_ = a.memory.Append(ctx, gateway.Message{
				Role:             gateway.RoleAssistant,
				Content:          replyBuilder.String(),
				ReasoningContent: reasoningBuilder.String(),
				ToolCalls:        toolCalls,
			})

			// 4. 收敛退出判断：若无工具调用，说明已得出最终回答，发送 EventDone 结束本轮交互
			if len(toolCalls) == 0 {
				sendEvent(ctx, outCh, protocol.Event{
					Type: protocol.EventDone,
					Usage: &protocol.Usage{
						PromptTokens:     totalTurnUsage.PromptTokens,
						CompletionTokens: totalTurnUsage.CompletionTokens,
						TotalTokens:      totalTurnUsage.TotalTokens,
					},
				})
				return
			}

			// 5. 执行工具调用流水线 (Gate 1/2/3 权限审查 -> 工具执行 -> 错误自愈)
			for _, tc := range toolCalls {
				sendEvent(ctx, outCh, protocol.Event{
					Type: protocol.EventToolCallStart,
					ToolCall: &protocol.ToolCallRecord{
						ID:        tc.ID,
						Name:      tc.Name,
						Arguments: string(tc.Arguments),
					},
				})

				// 权限门禁审查
				var allowed bool
				var denyReason string

				if permMgr != nil {
					origApprover := permMgr.Approver()
					if origApprover == nil {
						permMgr.SetApprover(permission.ApproverFunc(func(pCtx context.Context, req permission.Request) (permission.Decision, error) {
							reqID := fmt.Sprintf("perm_%d", atomic.AddUint64(&a.permSeq, 1))
							respCh := make(chan protocol.Decision, 1)

							a.pendingMu.Lock()
							a.pendingPerms[reqID] = respCh
							a.pendingMu.Unlock()

							defer func() {
								a.pendingMu.Lock()
								delete(a.pendingPerms, reqID)
								a.pendingMu.Unlock()
							}()

							if !sendEvent(pCtx, outCh, protocol.Event{
								Type: protocol.EventPermissionReq,
								Permission: &protocol.PermissionRequest{
									RequestID: reqID,
									ToolName:  req.ToolName,
									Arguments: string(req.Arguments),
									Reason:    req.Reason,
								},
							}) {
								return permission.DecisionDeny, pCtx.Err()
							}

							select {
							case d := <-respCh:
								switch d {
								case protocol.DecisionAllowOnce:
									return permission.DecisionAllowOnce, nil
								case protocol.DecisionAllowSession:
									return permission.DecisionAllowSession, nil
								default:
									return permission.DecisionDeny, nil
								}
							case <-pCtx.Done():
								return permission.DecisionDeny, pCtx.Err()
							}
						}))
					}

					var evalErr error
					allowed, denyReason, evalErr = permMgr.Evaluate(ctx, tc)
					if origApprover == nil {
						permMgr.SetApprover(nil) // 恢复状态
					}
					if evalErr != nil {
						allowed = false
						denyReason = "permission evaluation error: " + evalErr.Error()
					}
				} else {
					allowed = true
				}

				var res gateway.ToolResult

				if !allowed {
					// 权限未放行：以工具结果形式回传给模型（Error as Observation）
					res = gateway.ToolResult{
						ToolCallID: tc.ID,
						Name:       tc.Name,
						Content:    denyReason,
						IsError:    true,
					}
				} else {
					// 权限放行：分发给 Tool Registry 执行
					a.mu.RLock()
					tools := a.tools
					a.mu.RUnlock()

					var execErr error
					res, execErr = tools.Execute(ctx, tc)
					if execErr != nil && strings.TrimSpace(res.Content) == "" {
						res = gateway.ToolResult{
							ToolCallID: tc.ID,
							Name:       tc.Name,
							Content:    "Tool execution error: " + execErr.Error(),
							IsError:    true,
						}
					}
				}

				sendEvent(ctx, outCh, protocol.Event{
					Type: protocol.EventToolCallResult,
					ToolResult: &protocol.ToolResultRecord{
						ToolCallID: res.ToolCallID,
						Name:       res.Name,
						Content:    res.Content,
						IsError:    res.IsError,
					},
				})

				_ = a.memory.Append(ctx, gateway.Message{
					Role:       gateway.RoleTool,
					ToolResult: &res,
				})
			}
			// 继续下一步 ReAct 循环
		}

		sendEvent(ctx, outCh, protocol.Event{
			Type:  protocol.EventError,
			Error: ErrMaxSteps.Error(),
		})
	}()

	return outCh, nil
}

func sendEvent(ctx context.Context, ch chan<- protocol.Event, ev protocol.Event) bool {
	select {
	case ch <- ev:
		return true
	case <-ctx.Done():
		return false
	}
}
