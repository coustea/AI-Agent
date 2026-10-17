package agent

import (
	"errors"
	"fmt"
	"os"
	"strings"

	"my-agent/internal/config"
	"my-agent/internal/gateway"
	"my-agent/internal/memory"
	"my-agent/internal/permission"
	"my-agent/internal/protocol"
	"my-agent/internal/tool"
	"my-agent/internal/tool/builtin"
)

// Option 定义 Agent 的函数式拼装算子
type Option func(*CoreAgent)

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

// WithHook 挂载自定义生命周期横切切面钩子 (审计、链路监控等)
func WithHook(hook AgentHook) Option {
	return func(a *CoreAgent) {
		if hook != nil {
			a.hooks = append(a.hooks, hook)
		}
	}
}

// WithLoggingMiddleware 为 Agent 一键挂载透明可观测性日志中间件
func WithLoggingMiddleware(workDir ...string) Option {
	return func(a *CoreAgent) {
		dir := a.workDir
		if len(workDir) > 0 && strings.TrimSpace(workDir[0]) != "" {
			dir = strings.TrimSpace(workDir[0])
		}
		a.hooks = append(a.hooks, NewLoggingMiddleware(dir))
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
