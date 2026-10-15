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

	rel, err := filepath.Rel(workDirAbs, targetAbs)
	if err != nil || strings.HasPrefix(rel, "..") || rel == ".." {
		return "", fmt.Errorf("path escapes workspace: %s", cleanP)
	}

	return targetAbs, nil
}
