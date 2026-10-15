package agent

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"sync"

	"my-agent/internal/gateway"
	"my-agent/internal/memory"
	"my-agent/internal/tool"
	"my-agent/internal/tool/builtin"
)

var (
	ErrEmptyPrompt   = errors.New("agent: prompt cannot be empty")
	ErrNilGateway    = errors.New("agent: gateway client cannot be nil")
	ErrRunInProgress = errors.New("agent: another turn is already running")
	ErrMaxSteps      = errors.New("agent: exceeded maximum ReAct steps")
)

// BuildDefaultSystemPrompt 基于工作目录与本地长效记忆库构建 coustea 通用个人智能助手的系统提示词
func BuildDefaultSystemPrompt(workDir string) string {
	workDir = strings.TrimSpace(workDir)
	if workDir == "" {
		if wd, err := os.Getwd(); err == nil {
			workDir = wd
		}
	}

	bundle := memory.LoadBundle(workDir)
	memoryPrompt := bundle.FormatForPrompt()

	var sb strings.Builder
	sb.WriteString("You are coustea, an intelligent and versatile general-purpose local AI personal assistant.\n")
	sb.WriteString("You run directly on the user's local machine, helping with a wide range of tasks including reasoning, analysis, research, file management, system operations, writing, and daily workflows.\n")
	if workDir != "" {
		sb.WriteString(fmt.Sprintf("Working Directory: %s\n", workDir))
	}

	sb.WriteString("\nCore Guidelines:\n")
	sb.WriteString("- Understand user requests thoughtfully, thinking step-by-step when appropriate.\n")
	sb.WriteString("- Proactively use available tools (read_file, write_file, edit_file, glob, bash) whenever you need to explore files, run commands, or gather local context.\n")
	sb.WriteString("- Communicate clearly, concisely, and directly, using Chinese by default unless requested otherwise.\n")

	if memoryPrompt != "" {
		sb.WriteString("\n" + memoryPrompt + "\n")
	}

	return sb.String()
}

// EventType 定义 Agent 发送给调用方的流式事件类型
type EventType string

const (
	EventTextDelta      EventType = "text_delta"
	EventToolCallStart  EventType = "tool_call_start"
	EventToolCallResult EventType = "tool_call_result"
	EventDone           EventType = "done"
	EventError          EventType = "error"
)

// AgentEvent 是 Agent 向调用方发送的流式事件
type AgentEvent struct {
	Type       EventType
	Delta      string              // 文本流式增量
	ToolCall   *gateway.ToolCall   // 工具开始调用时携带
	ToolResult *gateway.ToolResult // 工具执行结束时携带
	Usage      *gateway.Usage      // 本轮 Token 消耗汇总
	Done       bool                // 对话是否完成
	Err        error               // 遇到的错误
}

// Agent 定义智能体调用的对外核心契约
type Agent interface {
	StreamRun(ctx context.Context, prompt string) (<-chan AgentEvent, error)
	Reset()
	SetGateway(gw gateway.Gateway)
	History() []gateway.Message
	SystemPrompt() string
	WorkDir() string
}

// Option 定义 Agent 的函数式拼装算子
type Option func(*CoreAgent)

// CoreAgent 是驱动 ReAct 循环的状态机核心
type CoreAgent struct {
	mu           sync.RWMutex
	gw           gateway.Gateway
	workDir      string
	memory       memory.Memory
	tools        *tool.Registry
	systemPrompt string
	maxSteps     int
	running      bool
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

// WithWorkDir 配置工作目录并自动更新系统提示词
func WithWorkDir(dir string) Option {
	return func(a *CoreAgent) {
		cleanDir := strings.TrimSpace(dir)
		if cleanDir != "" {
			a.workDir = cleanDir
			_ = memory.EnsureDirs(a.workDir)
			a.systemPrompt = BuildDefaultSystemPrompt(a.workDir)
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

// WithSystemPrompt 配置自定义系统提示词
func WithSystemPrompt(prompt string) Option {
	return func(a *CoreAgent) {
		if strings.TrimSpace(prompt) != "" {
			a.systemPrompt = strings.TrimSpace(prompt)
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

// NewAgent 使用函数式选项构建 CoreAgent 实例（严格遵守零 nil 默认装配原则）
func NewAgent(gw gateway.Gateway, opts ...Option) (*CoreAgent, error) {
	if gw == nil {
		return nil, ErrNilGateway
	}

	wd, _ := os.Getwd()
	_ = memory.EnsureDirs(wd)

	a := &CoreAgent{
		gw:           gw,
		workDir:      wd,
		memory:       memory.NewSlidingWindowMemory(40),
		tools:        tool.NewRegistry(),
		systemPrompt: BuildDefaultSystemPrompt(wd),
		maxSteps:     10,
	}

	for _, opt := range opts {
		opt(a)
	}

	return a, nil
}

// SetGateway 支持运行时热切换大模型网关，完整保留当前记忆与已注册工具
func (a *CoreAgent) SetGateway(gw gateway.Gateway) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if gw != nil {
		a.gw = gw
	}
}

// Reset 清空当前会话记忆
func (a *CoreAgent) Reset() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.memory.Clear()
}

// History 获取历史消息快照
func (a *CoreAgent) History() []gateway.Message {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.memory.History()
}

// SystemPrompt 获取当前生效的系统提示词
func (a *CoreAgent) SystemPrompt() string {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.systemPrompt
}

// WorkDir 获取当前绑定的工作目录
func (a *CoreAgent) WorkDir() string {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.workDir
}

// RegisterTools 动态增加工具
func (a *CoreAgent) RegisterTools(ts ...tool.Tool) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.tools.Register(ts...)
}

// StreamRun 驱动标准的 ReAct 状态循环，支持多轮交互、工具调用、错误自愈与流式打字输出
func (a *CoreAgent) StreamRun(ctx context.Context, prompt string) (<-chan AgentEvent, error) {
	prompt = strings.TrimSpace(prompt)
	if prompt == "" {
		return nil, ErrEmptyPrompt
	}

	if ctx == nil {
		ctx = context.Background()
	}

	a.mu.Lock()
	if a.running {
		a.mu.Unlock()
		return nil, ErrRunInProgress
	}
	a.running = true
	a.mu.Unlock()

	outCh := make(chan AgentEvent, 32)

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

		var totalTurnUsage gateway.Usage

		// 2. 驱动 ReAct 循环 (最多迭代 maxSteps 步)
		for step := 0; step < a.maxSteps; step++ {
			select {
			case <-ctx.Done():
				sendAgentEvent(ctx, outCh, AgentEvent{Type: EventError, Err: ctx.Err(), Done: true})
				return
			default:
			}

			a.mu.RLock()
			gw := a.gw
			toolDefs := a.tools.Definitions()
			sysPrompt := a.systemPrompt
			a.mu.RUnlock()

			// 基于记忆状态机安全构建当前上下文 (保证 Turn Atomicity 轮次原子性)
			reqMsgs, err := a.memory.BuildContext(ctx, sysPrompt)
			if err != nil {
				sendAgentEvent(ctx, outCh, AgentEvent{Type: EventError, Err: err, Done: true})
				return
			}

			// 发起网关流式调用
			stream, err := gw.ChatStream(ctx, &gateway.ChatRequest{
				Messages: reqMsgs,
				Tools:    toolDefs,
			})
			if err != nil {
				sendAgentEvent(ctx, outCh, AgentEvent{Type: EventError, Err: err, Done: true})
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
				}
				if chunk.Delta != "" {
					replyBuilder.WriteString(chunk.Delta)
					sendAgentEvent(ctx, outCh, AgentEvent{
						Type:  EventTextDelta,
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

			// 流式异常回滚原则：若网关流发生网络或协议错误中断，不得残留半截残缺消息破坏记忆
			if streamErr != nil {
				sendAgentEvent(ctx, outCh, AgentEvent{Type: EventError, Err: streamErr, Done: true})
				return
			}

			// 将模型本轮完整回复存入记忆
			_ = a.memory.Append(ctx, gateway.Message{
				Role:             gateway.RoleAssistant,
				Content:          replyBuilder.String(),
				ReasoningContent: reasoningBuilder.String(),
				ToolCalls:        toolCalls,
			})

			// 3. 收敛退出判断：若无工具调用，说明已得出最终回答，结束本轮交互
			if len(toolCalls) == 0 {
				sendAgentEvent(ctx, outCh, AgentEvent{
					Type:  EventDone,
					Usage: &totalTurnUsage,
					Done:  true,
				})
				return
			}

			// 4. 执行工具调用并回传观察结果（错误自愈原则：Error as Observation）
			for _, tc := range toolCalls {
				sendAgentEvent(ctx, outCh, AgentEvent{Type: EventToolCallStart, ToolCall: &tc})

				a.mu.RLock()
				tools := a.tools
				a.mu.RUnlock()

				res, execErr := tools.Execute(ctx, tc)
				if execErr != nil {
					res = gateway.ToolResult{
						ToolCallID: tc.ID,
						Name:       tc.Name,
						Content:    "Tool execution error: " + execErr.Error(),
						IsError:    true,
					}
				}

				sendAgentEvent(ctx, outCh, AgentEvent{Type: EventToolCallResult, ToolResult: &res})

				_ = a.memory.Append(ctx, gateway.Message{
					Role:       gateway.RoleTool,
					ToolResult: &res,
				})
			}
			// 继续下一步 ReAct 循环
		}

		sendAgentEvent(ctx, outCh, AgentEvent{
			Type: EventError,
			Err:  ErrMaxSteps,
			Done: true,
		})
	}()

	return outCh, nil
}

func sendAgentEvent(ctx context.Context, ch chan<- AgentEvent, ev AgentEvent) bool {
	select {
	case ch <- ev:
		return true
	case <-ctx.Done():
		return false
	}
}
