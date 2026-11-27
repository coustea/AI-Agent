// Package agent 的会话工作区命令执行后端（实现 Eino adk/filesystem.Shell）。
//
// 职责：
//   - 在 toolGuard 预检之后，于当前会话的隔离物理目录（Principal.Workspace）内启动独立子进程执行命令；
//   - 通过 cleanEnv 剥离服务进程敏感环境变量（DB_DSN / JWT_* / LLM_* / MYSQL_* / SEARCH_*），
//     并注入当前会话的 WORKSPACE 与只读 SKILLS_DIR 绝对路径；
//   - 区分三种终止语义：父上下文取消向上传播、单命令超时返回已产生输出供模型判断、非零退出码作为正常命令结果返回。
package agent

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	adkfs "github.com/cloudwego/eino/adk/filesystem"
)

type workspaceShell struct {
	timeout   time.Duration
	skillsDir string
}

// newShell 构造共享 Shell 后端；skillsDir 转为绝对路径供子进程 $SKILLS_DIR 使用。
func newShell(timeout time.Duration, skillsDir string) adkfs.Shell {
	if timeout <= 0 {
		timeout = 120 * time.Second
	}
	if s := strings.TrimSpace(skillsDir); s != "" {
		if abs, err := filepath.Abs(s); err == nil {
			skillsDir = abs
		}
	}
	return &workspaceShell{timeout: timeout, skillsDir: skillsDir}
}

// hostShell 按操作系统选择命令解释器，与 assemblePrompt 保持一致。
func hostShell() (name, flag string) {
	if runtime.GOOS == "windows" {
		return "cmd", "/C"
	}
	return "sh", "-c"
}

// Execute 在会话工作区执行单条命令，合并 stdout 与 stderr 供模型诊断。
func (s *workspaceShell) Execute(ctx context.Context, req *adkfs.ExecuteRequest) (*adkfs.ExecuteResponse, error) {
	p, err := PrincipalFrom(ctx)
	if err != nil {
		return nil, err
	}
	// 子超时继承父上下文取消信号；单命令超时不能延长整轮截止时间。
	runCtx, cancel := context.WithTimeout(ctx, s.timeout)
	defer cancel()

	name, flag := hostShell()
	cmd := exec.CommandContext(runCtx, name, flag, req.Command)
	cmd.Dir = p.Workspace
	cmd.Env = cleanEnv(p.Workspace, s.skillsDir)
	out, err := cmd.CombinedOutput()

	if ctx.Err() != nil {
		return nil, ctx.Err()
	}
	if runCtx.Err() != nil {
		return &adkfs.ExecuteResponse{Output: fmt.Sprintf("%s\n命令超时（%s）", out, s.timeout)}, nil
	}
	var exitErr *exec.ExitError
	// 非零退出码属于业务命令失败，返回给模型自行修正；仅进程无法启动等系统错向上报错。
	if err != nil && !errors.As(err, &exitErr) {
		return nil, err
	}
	code := cmd.ProcessState.ExitCode()
	return &adkfs.ExecuteResponse{Output: string(out), ExitCode: &code}, nil
}

// cleanEnv 保留 PATH 等运行时环境，剔除服务端凭据变量并注入本会话 WORKSPACE / SKILLS_DIR。
func cleanEnv(workspace, skillsDir string) []string {
	base := os.Environ()
	out := make([]string, 0, len(base)+2)
	for _, entry := range base {
		k, _, ok := strings.Cut(entry, "=")
		if !ok {
			continue
		}
		u := strings.ToUpper(strings.TrimSpace(k))
		if u == "WORKSPACE" || u == "SKILLS_DIR" || u == "DB_DSN" ||
			strings.HasPrefix(u, "JWT_") || strings.HasPrefix(u, "LLM_") ||
			strings.HasPrefix(u, "MYSQL_") || strings.HasPrefix(u, "SEARCH_") {
			continue
		}
		out = append(out, entry)
	}
	return append(out, "WORKSPACE="+workspace, "SKILLS_DIR="+skillsDir)
}
