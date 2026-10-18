package agent

import (
	"errors"
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

// Agent 直接指向统一数据契约层定义的 protocol.Agent 纯虚接口
type Agent = protocol.Agent

// CoreAgent 是基于 Harness 思想驱动 ReAct 循环与状态机管理的运行核心
type CoreAgent struct {
	mu           sync.RWMutex
	gw           gateway.Gateway
	cfg          *config.Config
	cfgPath      string
	workDir      string
	workDirRef   *builtin.WorkDirRef
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

// WorkDir 获取当前绑定的工作目录
func (a *CoreAgent) WorkDir() string {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.workDir
}

// MemoryCount 返回当前工作区生效的长期记忆篇数，供前端直接展示
func (a *CoreAgent) MemoryCount() int {
	a.mu.RLock()
	wd := a.workDir
	a.mu.RUnlock()
	bundle := memory.LoadBundle(wd)
	return len(bundle.GlobalFiles) + len(bundle.ProjectFiles)
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
