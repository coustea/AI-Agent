package builtin

import (
	"fmt"

	"my-agent/internal/fsutil"
)

// SafePath 解析并校验路径，确保文件操作严格限制在工作区内部。
// 边界判定（含符号链接解析）统一由 internal/fsutil 提供。
func SafePath(workDir, targetPath string) (string, error) {
	abs, inside := fsutil.ResolveInWorkspace(workDir, targetPath)
	if !inside {
		return "", fmt.Errorf("path escapes workspace: %s", targetPath)
	}
	return abs, nil
}
