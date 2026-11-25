package utils

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestSafeJoinRejectsTraversalAndSymlink(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	if _, err := SafeJoin(root, ".."); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf(".. 应被拒绝，得到 %v", err)
	}
	if _, err := SafeJoin(root, "a/b"); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("路径分隔符应被拒绝，得到 %v", err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "escape")); err != nil {
		t.Fatal(err)
	}
	if _, err := SafeJoin(root, "escape", "secret"); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("指向根外的软链接应被拒绝，得到 %v", err)
	}
	if _, err := SafeJoin(root, "user", "conversation"); err != nil {
		t.Fatalf("正常路径应允许，得到 %v", err)
	}
}
