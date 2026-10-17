//go:build windows

package builtin

import "os/exec"

// setupProcessGroup 在 Windows 平台上使用系统默认方式。
func setupProcessGroup(cmd *exec.Cmd) {
	// Windows 平台默认由 exec.CommandContext 驱动进程销毁
}
