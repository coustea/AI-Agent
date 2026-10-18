// Package fsutil 提供全仓唯一的工作区边界判定实现。
// 所有"路径是否允许访问"的裁决（工具沙箱、权限闸门）都必须经由本包，
// 避免各处重复实现导致规则漂移。
package fsutil

import (
	"os"
	"path/filepath"
	"strings"
)

// ResolveInWorkspace 判定 target 是否位于 workDir 或 ~/.tide 之内。
//
// 解析链：Abs → EvalSymlinks（对最近存在的祖先目录）→ 前缀判定。
// 符号链接全部解析后再比较，工作区内指向外部的软链（如 ln -s ~/.ssh ./evil）
// 将被正确判为越界；workDir 自身也做 EvalSymlinks（macOS /tmp → /private/tmp）。
// target 可以是不存在的新建路径（write_file 场景）：沿父目录链解析最近存在的祖先后拼回尾部。
func ResolveInWorkspace(workDir, target string) (abs string, inside bool) {
	target = strings.TrimSpace(target)
	if target == "" {
		return "", false
	}

	if strings.TrimSpace(workDir) == "" {
		if wd, err := os.Getwd(); err == nil {
			workDir = wd
		} else {
			workDir = "."
		}
	}

	workRoot := evalBestEffort(absClean(workDir))

	var targetAbs string
	if filepath.IsAbs(target) {
		targetAbs = filepath.Clean(target)
	} else {
		targetAbs = filepath.Join(workRoot, target)
	}
	targetReal := evalBestEffort(targetAbs)

	if withinPrefix(workRoot, targetReal) {
		return targetReal, true
	}

	// ~/.tide 白名单：全局记忆与配置目录
	if home, err := os.UserHomeDir(); err == nil && home != "" {
		if withinPrefix(evalBestEffort(filepath.Join(home, ".tide")), targetReal) {
			return targetReal, true
		}
	}

	return targetReal, false
}

// withinPrefix 判定 path 是否位于 root 目录之内（不含 root 自身时也视为之内）
func withinPrefix(root, path string) bool {
	root = filepath.Clean(root)
	path = filepath.Clean(path)
	rel, err := filepath.Rel(root, path)
	if err != nil {
		return false
	}
	return rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

func absClean(p string) string {
	if abs, err := filepath.Abs(p); err == nil {
		return filepath.Clean(abs)
	}
	return filepath.Clean(p)
}

// evalBestEffort 解析路径全部符号链接；路径不存在时沿父目录链解析最近存在的祖先后拼回尾部
func evalBestEffort(p string) string {
	if resolved, err := filepath.EvalSymlinks(p); err == nil {
		return resolved
	}

	// 路径（部分）不存在：逐级向上找最近存在的祖先
	dir := filepath.Dir(p)
	tail := filepath.Base(p)
	for dir != p {
		if resolved, err := filepath.EvalSymlinks(dir); err == nil {
			return filepath.Join(resolved, tail)
		}
		tail = filepath.Join(filepath.Base(dir), tail)
		dir = filepath.Dir(dir)
	}
	return p
}
