//go:build windows

package builtin

import (
	"context"
	"os/exec"
)

// setupProcessGroup 在 Windows 平台上使用系统默认方式。
func setupProcessGroup(cmd *exec.Cmd) {
	// Windows 平台默认由 exec.CommandContext 驱动进程销毁
}

// createShellCmd 在 Windows 平台上自适应选择可用的 shell 执行环境
func createShellCmd(ctx context.Context, command string) *exec.Cmd {
	// 优先使用 Git Bash 等环境中的 bash
	if _, err := exec.LookPath("bash"); err == nil {
		return exec.CommandContext(ctx, "bash", "-c", command)
	}
	// 其次使用系统自带的 PowerShell
	if _, err := exec.LookPath("powershell"); err == nil {
		return exec.CommandContext(ctx, "powershell", "-NoProfile", "-NonInteractive", "-Command", command)
	}
	// 最后回退到 cmd.exe
	return exec.CommandContext(ctx, "cmd", "/c", command)
}
