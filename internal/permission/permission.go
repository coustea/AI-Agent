package permission

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"

	"my-agent/internal/gateway"
)

// Decision 表示用户对权限请求的决策
type Decision int

const (
	DecisionDeny Decision = iota
	DecisionAllowOnce
	DecisionAllowSession
)

func (d Decision) String() string {
	switch d {
	case DecisionAllowOnce:
		return "allow_once"
	case DecisionAllowSession:
		return "allow_session"
	default:
		return "deny"
	}
}

// Request 封装需要审批的工具调用上下文与风险原因
type Request struct {
	ToolCallID string          `json:"tool_call_id"`
	ToolName   string          `json:"tool_name"`
	Arguments  json.RawMessage `json:"arguments"`
	WorkDir    string          `json:"work_dir"`
	Reason     string          `json:"reason"`
}

// Approver 定义人机交互或外部策略决策接口
type Approver interface {
	RequestApproval(ctx context.Context, req Request) (Decision, error)
}

// ApproverFunc 便捷的函数式 Approver 实现
type ApproverFunc func(ctx context.Context, req Request) (Decision, error)

func (f ApproverFunc) RequestApproval(ctx context.Context, req Request) (Decision, error) {
	return f(ctx, req)
}

// 默认硬拒绝列表 (Gate 1: 永远禁止执行)
var defaultHardDenyList = []string{
	"rm -rf /",
	"rm -rf /*",
	"sudo ",
	"shutdown",
	"reboot",
	"mkfs",
	"dd if=",
	"> /dev/sda",
	":(){ :|:& };:",
}

var destructiveWordPattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n])\s*(?:rm|del|rmdir)(?:\s+-[rf]+)?\s+`)

// Manager 实现基于 Harness 思想的三道闸门权限管线
type Manager struct {
	mu             sync.RWMutex
	workDir        string
	approver       Approver
	hardDenyList   []string
	sessionAllowed map[string]bool // key 格式: "tool:signature"
	alwaysAskBash  bool
	autoApprove    bool
}

// Option 定义 Manager 配置项
type Option func(*Manager)

// WithApprover 设置用户审批回调器
func WithApprover(approver Approver) Option {
	return func(m *Manager) {
		m.approver = approver
	}
}

// WithHardDenyList 自定义硬拒绝规则列表
func WithHardDenyList(denyList []string) Option {
	return func(m *Manager) {
		if len(denyList) > 0 {
			m.hardDenyList = append([]string(nil), denyList...)
		}
	}
}

// WithAlwaysAskBash 设置是否对所有 Bash 命令强制要求用户审批
func WithAlwaysAskBash(always bool) Option {
	return func(m *Manager) {
		m.alwaysAskBash = always
	}
}

// WithAutoApprove 设置是否全自动放行非硬拒绝操作 (常用于非交互测试或可信自动化模式)
func WithAutoApprove(auto bool) Option {
	return func(m *Manager) {
		m.autoApprove = auto
	}
}

// NewManager 创建三道闸门权限管理器实例
func NewManager(workDir string, opts ...Option) *Manager {
	cleanDir := strings.TrimSpace(workDir)
	if cleanDir == "" {
		if wd, err := os.Getwd(); err == nil {
			cleanDir = wd
		} else {
			cleanDir = "."
		}
	}
	absDir, err := filepath.Abs(cleanDir)
	if err == nil {
		cleanDir = absDir
	}

	m := &Manager{
		workDir:        cleanDir,
		hardDenyList:   append([]string(nil), defaultHardDenyList...),
		sessionAllowed: make(map[string]bool),
		alwaysAskBash:  true, // 遵循安全默认值：执行任何 Shell 命令前提示用户确认
	}

	for _, opt := range opts {
		opt(m)
	}

	return m
}

// SetApprover 动态设置用户审批器
func (m *Manager) SetApprover(approver Approver) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.approver = approver
}

// Approver 获取当前配置的审批器
func (m *Manager) Approver() Approver {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.approver
}

// SetAutoApprove 动态设置是否全自动放行非硬拒绝操作
func (m *Manager) SetAutoApprove(auto bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.autoApprove = auto
}

// Evaluate 执行三道闸门权限决策管线：
// Gate 1: 硬拒绝表 (Hard Deny List) -> 命中直接返回 false，无需人工介入
// Gate 2: 规则匹配器 (Rule Evaluator) -> 判断是否存在破坏性操作或越界行为
// Gate 3: 交互式审批 (Interactive Approval) -> 触发人类介入确认并支持会话级信任
func (m *Manager) Evaluate(ctx context.Context, call gateway.ToolCall) (allowed bool, reason string, err error) {
	// --- Gate 1: 硬拒绝表检查 ---
	if blocked, denyReason := m.checkHardDeny(call); blocked {
		return false, denyReason, nil
	}

	// --- Gate 2: 风险规则匹配 ---
	needsApproval, ruleReason := m.checkRules(call)
	if !needsApproval {
		// 常规安全操作，无需审批直接放行
		return true, "", nil
	}

	// 检查当前会话是否已经授信放行该操作
	sig := m.callSignature(call)
	m.mu.RLock()
	if m.sessionAllowed[sig] {
		m.mu.RUnlock()
		return true, "", nil
	}
	m.mu.RUnlock()

	// 若处于自动放行模式 (如特定自动化测试)，直接通过
	if m.autoApprove {
		return true, "", nil
	}

	// --- Gate 3: 人工交互审批 ---
	if m.approver == nil {
		// 没有配置审批通道时，基于安全默认原则拒绝高危操作
		return false, fmt.Sprintf("permission denied: risk detected (%s) but no approver configured", ruleReason), nil
	}

	req := Request{
		ToolCallID: call.ID,
		ToolName:   call.Name,
		Arguments:  call.Arguments,
		WorkDir:    m.workDir,
		Reason:     ruleReason,
	}

	decision, err := m.approver.RequestApproval(ctx, req)
	if err != nil {
		return false, "", fmt.Errorf("permission approval error: %w", err)
	}

	switch decision {
	case DecisionAllowSession:
		m.mu.Lock()
		m.sessionAllowed[sig] = true
		m.mu.Unlock()
		return true, "", nil

	case DecisionAllowOnce:
		return true, "", nil

	case DecisionDeny:
		fallthrough
	default:
		return false, fmt.Sprintf("permission denied by user: %s", ruleReason), nil
	}
}

// checkHardDeny 检查 Gate 1: 绝对不可执行的硬拒绝指令
func (m *Manager) checkHardDeny(call gateway.ToolCall) (bool, string) {
	if call.Name != "bash" {
		return false, ""
	}

	cmd := extractStringArg(call.Arguments, "command")
	if cmd == "" {
		return false, ""
	}

	for _, pattern := range m.hardDenyList {
		if strings.Contains(cmd, pattern) {
			return true, fmt.Sprintf("blocked by Gate 1 (Hard Deny): '%s' is on the deny list", pattern)
		}
	}

	return false, ""
}

// checkRules 检查 Gate 2: 规则匹配与风险识别
func (m *Manager) checkRules(call gateway.ToolCall) (bool, string) {
	switch call.Name {
	case "bash":
		cmd := extractStringArg(call.Arguments, "command")
		if cmd == "" {
			return true, "empty shell command"
		}

		// 1. 检查破坏性指令
		if destructiveWordPattern.MatchString(cmd) || strings.Contains(cmd, "chmod 777") || strings.Contains(cmd, "> /etc/") {
			return true, fmt.Sprintf("potentially destructive shell command: %s", cmd)
		}

		// 2. 检查全局 bash 审批策略
		if m.alwaysAskBash {
			return true, fmt.Sprintf("shell command execution: %s", cmd)
		}

	case "read_file", "write_file", "edit_file":
		path := extractStringArg(call.Arguments, "path")
		if path == "" {
			return true, "empty file path"
		}

		if escapes, targetAbs := m.isPathEscapingWorkspace(path); escapes {
			return true, fmt.Sprintf("file access outside workspace (%s): %s", call.Name, targetAbs)
		}

	case "glob":
		// glob 搜索默认属于安全只读操作，直接放行
		return false, ""
	}

	return false, ""
}

// isPathEscapingWorkspace 校验目标文件路径是否逃逸了当前项目工作区和用户 ~/.coustea 目录
func (m *Manager) isPathEscapingWorkspace(p string) (bool, string) {
	cleanP := strings.TrimSpace(p)
	if cleanP == "" {
		return true, ""
	}

	var targetAbs string
	if filepath.IsAbs(cleanP) {
		targetAbs = filepath.Clean(cleanP)
	} else {
		targetAbs = filepath.Clean(filepath.Join(m.workDir, cleanP))
	}

	// 1. 位于当前项目工作区内，合法
	relWork, errWork := filepath.Rel(m.workDir, targetAbs)
	if errWork == nil && !strings.HasPrefix(relWork, "..") && relWork != ".." {
		return false, targetAbs
	}

	// 2. 位于用户 ~/.coustea 目录下（全局记忆/配置），合法
	home, errHome := os.UserHomeDir()
	if errHome == nil && home != "" {
		globalCousteaAbs := filepath.Clean(filepath.Join(home, ".coustea"))
		relGlobal, errRelGlobal := filepath.Rel(globalCousteaAbs, targetAbs)
		if errRelGlobal == nil && !strings.HasPrefix(relGlobal, "..") && relGlobal != ".." {
			return false, targetAbs
		}
	}

	return true, targetAbs
}

func (m *Manager) callSignature(call gateway.ToolCall) string {
	switch call.Name {
	case "bash":
		cmd := strings.TrimSpace(extractStringArg(call.Arguments, "command"))
		return "bash:" + cmd
	case "read_file", "write_file", "edit_file":
		path := strings.TrimSpace(extractStringArg(call.Arguments, "path"))
		return call.Name + ":" + path
	default:
		return call.Name + ":" + string(call.Arguments)
	}
}

func extractStringArg(raw json.RawMessage, key string) string {
	if len(raw) == 0 {
		return ""
	}
	var m map[string]any
	if err := json.Unmarshal(raw, &m); err != nil {
		return ""
	}
	val, ok := m[key]
	if !ok {
		return ""
	}
	s, ok := val.(string)
	if !ok {
		return ""
	}
	return s
}
