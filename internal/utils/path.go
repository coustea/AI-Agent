package utils

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

var ErrUnsafePath = errors.New("路径超出允许范围")

// SafeJoin 只接受单层路径段，并拒绝指向根目录外的符号链接。
func SafeJoin(root string, names ...string) (string, error) {
	base, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	for _, name := range names {
		if name == "" || name == "." || name == ".." || filepath.Base(name) != name || strings.ContainsAny(name, `/\`) {
			return "", ErrUnsafePath
		}
	}
	target := filepath.Join(append([]string{base}, names...)...)
	realBase, err := filepath.EvalSymlinks(base)
	if err != nil {
		if !os.IsNotExist(err) {
			return "", fmt.Errorf("解析根路径失败: %w", err)
		}
		realBase = base
	}
	probe := target
	for {
		if _, err := os.Lstat(probe); err == nil {
			break
		}
		parent := filepath.Dir(probe)
		if parent == probe {
			return "", ErrUnsafePath
		}
		probe = parent
	}
	realProbe, err := filepath.EvalSymlinks(probe)
	if err != nil {
		return "", fmt.Errorf("解析路径失败: %w", err)
	}
	rel, err := filepath.Rel(realBase, realProbe)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", ErrUnsafePath
	}
	return target, nil
}

// ClipRunes 按 Unicode 字符数截断字符串（不追加省略号）。
func ClipRunes(s string, maxRunes int) string {
	r := []rune(s)
	if len(r) <= maxRunes {
		return s
	}
	return string(r[:maxRunes])
}

// Truncate 按 Unicode 字符数截断字符串，超长时追加省略号。
func Truncate(s string, maxRunes int) string {
	r := []rune(s)
	if len(r) <= maxRunes {
		return s
	}
	return string(r[:maxRunes]) + "…"
}
