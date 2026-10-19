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

	"my-agent/internal/fsutil"
	"my-agent/internal/protocol"
)

// Approver 定义人机交互或外部策略决策接口
type Approver interface {
	RequestApproval(ctx context.Context, req protocol.PermissionRequest) (protocol.Decision, error)
}

// ApproverFunc 便捷的函数式 Approver 实现
type ApproverFunc func(ctx context.Context, req protocol.PermissionRequest) (protocol.Decision, error)

func (f ApproverFunc) RequestApproval(ctx context.Context, req protocol.PermissionRequest) (protocol.Decision, error) {
	return f(ctx, req)
}

// Gate 1 硬拒绝正则表（永远禁止执行，无需人工审批）。
// 注意 rm 作用于根或根下通配才硬拒；rm -rf /tmp/x 等落到 Gate 2 走人工审批。
var defaultHardDenyPatterns = []*regexp.Regexp{
	// rm 任何形式作用于根目录或根下通配
	regexp.MustCompile(`(?i)(?:^|[;&|()\n"'\x60])\s*rm\s+(?:-{1,2}[a-zA-Z]+\s+)*(?:/(?:\s|\*|$)|/\*)`),
	// 提权与系统级电源/格式化操作
	regexp.MustCompile(`(?i)(?:^|[;&|()\n"'\x60])\s*(?:sudo|shutdown|reboot|mkfs)\b`),
	// 低级磁盘镜像写入
	regexp.MustCompile(`(?i)(?:^|[;&|()\n"'\x60])\s*dd\s+[^|]*\bif=`),
	// 直接向块设备写入
	regexp.MustCompile(`>{1,2}\s*/dev/(?:sd|disk|nvme)`),
	// fork 炸弹
	regexp.MustCompile(`:\(\)\s*\{\s*:\|:&\s*\}\s*;:`),
}

var (
	// 文件与目录破坏性删除 (rm, rmdir, unlink, shred, del)，支持前置引号、反引号以及 xargs 包装
	destructiveWordPattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n"'\x60]|\bxargs\s+)\s*(?:rm|rmdir|unlink|shred|del)(?:\s+-[a-zA-Z]+)*\s+`)

	// find 命令中携带破坏性删除 (-delete)
	findDeletePattern = regexp.MustCompile(`(?i)\bfind\b.*\s+-delete(?:\s+|$)`)

	// Git 破坏性或强覆盖操作 (强制回滚、强制推送、强制清理、丢弃更改)，支持前置引号包装
	gitDangerousPattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n"'\x60])\s*git\s+(?:reset\s+--hard|clean\s+-[a-zA-Z]*f|restore\s+\.|checkout\s+\.|push\s+.*(?:-f|--force))(?:\s+|["'\x60]|$)`)

	// 权限与属组篡改
	permChangePattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n"'\x60]|\bxargs\s+)\s*(?:chmod|chown|chgrp)\s+`)

	// 进程销毁与强制终止
	processKillPattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n"'\x60]|\bxargs\s+)\s*(?:kill|pkill|killall)\s+`)

	// 远程脚本管道直接执行 (如 curl ... | sh, wget ... | bash)
	remotePipeExecPattern = regexp.MustCompile(`(?i)(?:curl|wget)\s+[^|;]+\|\s*(?:sh|bash|zsh)`)

	// 重定向篡改系统核心目录
	systemDirWritePattern = regexp.MustCompile(`(?:>|>>)\s*/(?:etc|usr|bin|sbin|System|Library)/`)

	// 磁盘擦除与低级分区操作
	diskManipulatePattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n"'\x60])\s*(?:dd|fdisk|parted|mkfs|format)\s+`)
)

// checkDangerousBashCommand 判定命令是否属于破坏性或高风险操作
func checkDangerousBashCommand(cmd string) (isDangerous bool, reason string) {
	clean := strings.TrimSpace(cmd)
	if clean == "" {
		return false, ""
	}

	if destructiveWordPattern.MatchString(clean) {
		return true, fmt.Sprintf("file deletion: %s", clean)
	}
	if findDeletePattern.MatchString(clean) {
		return true, fmt.Sprintf("find with deletion: %s", clean)
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
	mu               sync.RWMutex
	workDir          string
	approver         Approver
	hardDenyPatterns []*regexp.Regexp
	sessionAllowed   map[string]bool // key 格式: "tool:signature"
	autoApprove      bool
}

// Option 定义 Manager 配置项
type Option func(*Manager)

// WithApprover 设置用户审批回调器
func WithApprover(approver Approver) Option {
	return func(m *Manager) {
		m.approver = approver
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
		workDir:          cleanDir,
		hardDenyPatterns: append([]*regexp.Regexp(nil), defaultHardDenyPatterns...),
		sessionAllowed:   make(map[string]bool),
	}

	for _, opt := range opts {
		opt(m)
	}

	return m
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

	req := protocol.PermissionRequest{
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
	case protocol.DecisionAllowSession:
		m.mu.Lock()
		m.sessionAllowed[sig] = true
		m.mu.Unlock()
		return true, "", nil

	case protocol.DecisionAllowOnce:
		return true, "", nil

	default:
		// DecisionDeny 与任何未知决策一律拒绝：审批层必须 fail-closed
		return false, fmt.Sprintf("permission denied by user: %s", ruleReason), nil
	}
}

// checkHardDeny 检查 Gate 1: 绝对不可执行的硬拒绝指令
func (m *Manager) checkHardDeny(call protocol.ToolCall) (blocked bool, denyReason string) {
	if call.Name != "bash" {
		return false, ""
	}

	cmd := extractStringArg(call.Arguments, "command")
	if cmd == "" {
		return false, ""
	}

	m.mu.RLock()
	patterns := m.hardDenyPatterns
	m.mu.RUnlock()

	for _, re := range patterns {
		if re.MatchString(cmd) {
			return true, fmt.Sprintf("blocked by Gate 1 (Hard Deny): command matches deny pattern %q", re.String())
		}
	}

	return false, ""
}

// checkRules 检查 Gate 2: 规则匹配与风险识别
func (m *Manager) checkRules(call protocol.ToolCall) (needsApproval bool, ruleReason string) {
	switch call.Name {
	case "bash":
		cmd := extractStringArg(call.Arguments, "command")
		if cmd == "" {
			return true, "empty shell command"
		}

		// 命令规范化分析：展开包装与间接执行，收集叶子段与重定向目标
		analysis := analyzeCommand(cmd)
		if analysis.suspicious {
			return true, "command uses indirect execution (interpreter inline / eval / command substitution) and cannot be statically analyzed"
		}

		// 叶子段逐个跑危险特征正则表
		for _, leaf := range analysis.leaves {
			if isDangerous, reason := checkDangerousBashCommand(leaf); isDangerous {
				return true, fmt.Sprintf("potentially destructive shell command: %s", reason)
			}
		}

		// 覆盖重定向：目标为工作区内已存在文件时才升级审批（新建文件与 write_file 行为等价，放行）
		for _, target := range analysis.redirectTargets {
			if m.overwritesExistingFile(target) {
				return true, fmt.Sprintf("overwrite redirection to existing file: %s", target)
			}
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

	case "glob", "grep":
		// glob 与 grep 搜索默认属于安全只读操作，直接放行
		return false, ""
	}

	return false, ""
}

// isPathEscapingWorkspace 校验目标文件路径是否逃逸了当前项目工作区和用户 ~/.tide 目录。
// 边界判定（含符号链接解析）统一由 internal/fsutil 提供。
func (m *Manager) isPathEscapingWorkspace(targetPath string) (escapes bool, resolvedAbs string) {
	m.mu.RLock()
	workDir := m.workDir
	m.mu.RUnlock()

	abs, inside := fsutil.ResolveInWorkspace(workDir, targetPath)
	return !inside, abs
}

// overwritesExistingFile 判定重定向目标是否为工作区内已存在的常规文件
func (m *Manager) overwritesExistingFile(target string) bool {
	clean := strings.TrimSpace(target)
	if clean == "" {
		return false
	}
	abs := clean
	if !filepath.IsAbs(clean) {
		m.mu.RLock()
		abs = filepath.Join(m.workDir, clean)
		m.mu.RUnlock()
	}
	info, err := os.Stat(abs)
	return err == nil && info.Mode().IsRegular()
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

func extractStringArg(raw, key string) string {
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
