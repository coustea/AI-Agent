package builtin

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// SafePath 解析并校验路径，确保文件操作严格限制在工作区内部，防止路径遍历逃逸（如 ../../）
func SafePath(workDir, p string) (string, error) {
	cleanP := strings.TrimSpace(p)
	if cleanP == "" {
		return "", fmt.Errorf("path cannot be empty")
	}

	if workDir == "" {
		wd, err := os.Getwd()
		if err != nil {
			return "", fmt.Errorf("failed to get current working directory: %w", err)
		}
		workDir = wd
	}

	workDirAbs, err := filepath.Abs(workDir)
	if err != nil {
		return "", fmt.Errorf("failed to get absolute workdir: %w", err)
	}

	var targetAbs string
	if filepath.IsAbs(cleanP) {
		targetAbs = filepath.Clean(cleanP)
	} else {
		targetAbs = filepath.Join(workDirAbs, cleanP)
	}
	targetAbs, err = filepath.Abs(targetAbs)
	if err != nil {
		return "", fmt.Errorf("failed to resolve target path: %w", err)
	}

	// 1. 检查是否在当前工作区内部
	relWork, errWork := filepath.Rel(workDirAbs, targetAbs)
	if errWork == nil && !strings.HasPrefix(relWork, "..") && relWork != ".." {
		return targetAbs, nil
	}

	// 2. 检查是否在用户全局 ~/.coustea 目录内部（允许读取与沉淀全局记忆及配置）
	home, errHome := os.UserHomeDir()
	if errHome == nil && home != "" {
		globalCousteaAbs, errGlobal := filepath.Abs(filepath.Join(home, ".coustea"))
		if errGlobal == nil {
			relGlobal, errRelGlobal := filepath.Rel(globalCousteaAbs, targetAbs)
			if errRelGlobal == nil && !strings.HasPrefix(relGlobal, "..") && relGlobal != ".." {
				return targetAbs, nil
			}
		}
	}

	return "", fmt.Errorf("path escapes workspace: %s", cleanP)
}
