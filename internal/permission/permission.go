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

	"my-agent/internal/protocol"
)

// Decision 统一采用 protocol.Decision 决策枚举
type Decision = protocol.Decision

const (
	DecisionDeny         = protocol.DecisionDeny
	DecisionAllowOnce    = protocol.DecisionAllowOnce
	DecisionAllowSession = protocol.DecisionAllowSession
)

// Request 统一采用 protocol.PermissionRequest 纯数据契约
type Request = protocol.PermissionRequest

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

var (
	// 文件与目录破坏性删除 (rm, rmdir, unlink, shred, del)
	destructiveWordPattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n])\s*(?:rm|rmdir|unlink|shred|del)(?:\s+-[a-zA-Z]+)*\s+`)

	// Git 破坏性或强覆盖操作 (强制回滚、强制推送、强制清理、丢弃更改)
	gitDangerousPattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n])\s*git\s+(?:reset\s+--hard|clean\s+-[a-zA-Z]*f|restore\s+\.|checkout\s+\.|push\s+.*(?:-f|--force))(?:\s+|$)`)

	// 权限与属组篡改
	permChangePattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n])\s*(?:chmod|chown|chgrp)\s+`)

	// 进程销毁与强制终止
	processKillPattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n])\s*(?:kill|pkill|killall)\s+`)

	// 远程脚本管道直接执行 (如 curl ... | sh, wget ... | bash)
	remotePipeExecPattern = regexp.MustCompile(`(?i)(?:curl|wget)\s+[^|;]+\|\s*(?:sh|bash|zsh)`)

	// 重定向篡改系统核心目录
	systemDirWritePattern = regexp.MustCompile(`(?:>|>>)\s*/(?:etc|usr|bin|sbin|System|Library)/`)

	// 磁盘擦除与低级分区操作
	diskManipulatePattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n])\s*(?:dd|fdisk|parted|mkfs|format)\s+`)
)

// checkDangerousBashCommand 判定命令是否属于破坏性或高风险操作
func checkDangerousBashCommand(cmd string) (bool, string) {
	clean := strings.TrimSpace(cmd)
	if clean == "" {
		return false, ""
	}

	if destructiveWordPattern.MatchString(clean) {
		return true, fmt.Sprintf("file deletion: %s", clean)
	}
	if gitDangerousPattern.MatchString(clean) {
		return true, fmt.Sprintf("destructive git operation: %s", clean)
	}
	if permChangePattern.MatchString(clean) {
		return true, fmt.Sprintf("permission modification: %s", clean)
	}
	if processKillPattern.MatchString(clean) {
		return true, fmt.Sprintf("process termination: %s", clean)
	}
	if remotePipeExecPattern.MatchString(clean) {
		return true, fmt.Sprintf("remote script pipe execution: %s", clean)
	}
	if systemDirWritePattern.MatchString(clean) {
		return true, fmt.Sprintf("writing to system directory: %s", clean)
	}
	if diskManipulatePattern.MatchString(clean) {
		return true, fmt.Sprintf("disk manipulation command: %s", clean)
	}

	return false, ""
}

// Manager 实现基于 Harness 思想的三道闸门权限管线
type Manager struct {
	mu             sync.RWMutex
	workDir        string
	approver       Approver
	hardDenyList   []string
	sessionAllowed map[string]bool // key 格式: "tool:signature"
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

// SetWorkDir 原地更新工作目录，保留现有审批器、信任表与自动放行状态
func (m *Manager) SetWorkDir(workDir string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	cleanDir := strings.TrimSpace(workDir)
	if cleanDir == "" {
		if wd, err := os.Getwd(); err == nil {
			cleanDir = wd
		} else {
			cleanDir = "."
		}
	}
	if absDir, err := filepath.Abs(cleanDir); err == nil {
		cleanDir = absDir
	}
	m.workDir = cleanDir
}

// Evaluate 执行三道闸门权限决策管线：
// Gate 1: 硬拒绝表 (Hard Deny List) -> 命中直接返回 false，无需人工介入
// Gate 2: 规则匹配器 (Rule Evaluator) -> 判断是否存在破坏性操作或越界行为
// Gate 3: 交互式审批 (Interactive Approval) -> 触发人类介入确认并支持会话级信任
func (m *Manager) Evaluate(ctx context.Context, call protocol.ToolCall) (allowed bool, reason string, err error) {
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
func (m *Manager) checkHardDeny(call protocol.ToolCall) (bool, string) {
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
func (m *Manager) checkRules(call protocol.ToolCall) (bool, string) {
	switch call.Name {
	case "bash":
		cmd := extractStringArg(call.Arguments, "command")
		if cmd == "" {
			return true, "empty shell command"
		}

		// 检查是否命中危险/破坏性操作特征 (未命中则直接放行)
		if isDangerous, reason := checkDangerousBashCommand(cmd); isDangerous {
			return true, fmt.Sprintf("potentially destructive shell command: %s", reason)
		}

		return false, ""

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

func (m *Manager) callSignature(call protocol.ToolCall) string {
	switch call.Name {
	case "bash":
		cmd := strings.TrimSpace(extractStringArg(call.Arguments, "command"))
		return "bash:" + cmd
	case "read_file", "write_file", "edit_file":
		path := strings.TrimSpace(extractStringArg(call.Arguments, "path"))
		return call.Name + ":" + path
	default:
		return call.Name + ":" + call.Arguments
	}
}

func extractStringArg(raw string, key string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}
	var m map[string]any
	if err := json.Unmarshal([]byte(raw), &m); err != nil {
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
