//go:build !windows

package builtin

import (
	"os/exec"
	"syscall"
)

// setupProcessGroup 为命令配置独立的进程组，确保超时或取消时能够彻底杀死派生出的所有子进程，避免孤儿进程残留。
func setupProcessGroup(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		if cmd.Process == nil || cmd.Process.Pid <= 0 {
			return nil
		}
		// 向负数 PID（即整个进程组）发送 SIGKILL 信号
		return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
	}
}
