package tools

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"
)

const (
	defaultShellTimeout = 120 * time.Second
	maxShellOutputRunes = 50000
)

// ShellConfig 是通用命令执行工具 execute 的配置参数。
type ShellConfig struct {
	Timeout     time.Duration
	SkillsDir   string
	WorkspaceOf func(context.Context) (string, error)
}

// ShellInput 是 execute 工具的入参。
type ShellInput struct {
	Command string `json:"command" jsonschema:"description=要在当前会话工作区执行的 Shell 命令"`
}

// HostShellInfo 返回当前宿主机操作系统/架构与默认 Shell 名称，供提示词与工具描述告知 Agent。
func HostShellInfo() (osArch, shellName string) {
	osArch = runtime.GOOS + "/" + runtime.GOARCH
	if runtime.GOOS == "windows" {
		return osArch, "cmd"
	}
	if _, err := exec.LookPath("bash"); err == nil {
		return osArch, "bash"
	}
	return osArch, "sh"
}

// shellCommand 按当前操作系统构造类似 subprocess.run(command, shell=True) 的命令对象。
func shellCommand(ctx context.Context, command string) *exec.Cmd {
	if runtime.GOOS == "windows" {
		return exec.CommandContext(ctx, "cmd", "/C", command)
	}
	if bash, err := exec.LookPath("bash"); err == nil {
		return exec.CommandContext(ctx, bash, "-c", command)
	}
	return exec.CommandContext(ctx, "/bin/sh", "-c", command)
}

// NewShell 构造通用跨平台命令执行工具：只负责在会话工作区执行命令并返回输出，
// 高危命令与只读目录拦截统一由 ToolGuard 中间件处理。
func NewShell(cfg ShellConfig) (tool.InvokableTool, error) {
	if cfg.WorkspaceOf == nil {
		return nil, fmt.Errorf("工作区解析函数未配置")
	}
	timeout := cfg.Timeout
	if timeout <= 0 {
		timeout = defaultShellTimeout
	}
	var absSkills string
	if s := strings.TrimSpace(cfg.SkillsDir); s != "" {
		if abs, err := filepath.Abs(s); err == nil {
			absSkills = abs
		}
	}

	osArch, shellName := HostShellInfo()
	desc := fmt.Sprintf(
		"在当前会话工作区执行 %s 命令（当前系统：%s）。命令默认在工作区目录内运行，已注入 WORKSPACE 与 SKILLS_DIR 环境变量；仅用于真实任务执行与检查。",
		shellName, osArch,
	)

	// shortcut: 仅通过 exec.CommandContext 终止主进程，不按平台拆分独立进程组强杀；若后续遇到后台孤儿进程残留再补充。
	return utils.InferTool(ToolExecute, desc, func(ctx context.Context, in ShellInput) (string, error) {
		workspace, err := cfg.WorkspaceOf(ctx)
		if err != nil {
			return "", err
		}
		if strings.TrimSpace(in.Command) == "" {
			return "", fmt.Errorf("command 不能为空")
		}
		tmpDir := filepath.Join(workspace, ".tmp")
		if err := os.MkdirAll(tmpDir, 0o700); err != nil {
			return "", fmt.Errorf("创建工作区临时目录失败: %w", err)
		}

		cmdCtx, cancel := context.WithTimeout(ctx, timeout)
		defer cancel()

		cmd := shellCommand(cmdCtx, in.Command)
		cmd.Dir = workspace
		cmd.Env = filterEnv(os.Environ(), workspace, tmpDir, absSkills)

		raw, runErr := cmd.CombinedOutput()
		if cmdCtx.Err() == context.DeadlineExceeded {
			return fmt.Sprintf("Error: Timeout (%s)", timeout), nil
		}
		if ctx.Err() != nil {
			return "", ctx.Err()
		}
		if runErr != nil && cmd.ProcessState == nil {
			return fmt.Sprintf("Error: %v", runErr), nil
		}

		out := strings.TrimSpace(string(raw))
		if cmd.ProcessState != nil && cmd.ProcessState.ExitCode() != 0 {
			codeLine := fmt.Sprintf("[exit code %d]", cmd.ProcessState.ExitCode())
			if out == "" {
				out = codeLine
			} else {
				out += "\n" + codeLine
			}
		}
		if out == "" {
			return "(no output)", nil
		}
		return truncate(out, maxShellOutputRunes), nil
	})
}

// filterEnv 继承宿主机运行环境以支持三平台工具链，同时剔除应用密钥变量并注入工作区环境变量。
func filterEnv(base []string, workspace, tmpDir, skillsDir string) []string {
	out := make([]string, 0, len(base)+5)
	for _, entry := range base {
		k, _, ok := strings.Cut(entry, "=")
		if !ok || isSensitiveOrManagedEnv(k) {
			continue
		}
		out = append(out, entry)
	}
	out = append(out,
		"WORKSPACE="+workspace,
		"TMPDIR="+tmpDir,
		"TEMP="+tmpDir,
		"TMP="+tmpDir,
	)
	if skillsDir != "" {
		out = append(out, "SKILLS_DIR="+skillsDir)
	}
	return out
}

// isSensitiveOrManagedEnv 识别需屏蔽的密钥配置或由本工具接管覆盖的环境变量名。
func isSensitiveOrManagedEnv(key string) bool {
	u := strings.ToUpper(strings.TrimSpace(key))
	switch u {
	case "WORKSPACE", "SKILLS_DIR", "TMPDIR", "TEMP", "TMP", "DB_DSN":
		return true
	}
	for _, prefix := range []string{"MYSQL_", "JWT_", "LLM_", "SEARCH_"} {
		if strings.HasPrefix(u, prefix) {
			return true
		}
	}
	for _, sub := range []string{"SECRET", "PASSWORD", "TOKEN", "API_KEY", "PRIVATE_KEY"} {
		if strings.Contains(u, sub) {
			return true
		}
	}
	return false
}
