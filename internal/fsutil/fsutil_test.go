package fsutil

import (
	"os"
	"path/filepath"
	"testing"
)

func TestResolveInWorkspace_BasicBoundary(t *testing.T) {
	tmpDir := t.TempDir()

	cases := []struct {
		name   string
		target string
		inside bool
	}{
		{"empty", "  ", false},
		{"relative inside", "src/main.go", true},
		{"dot inside", "./a/../b.txt", true},
		{"escape via dotdot", "../../etc/passwd", false},
		{"absolute inside", filepath.Join(tmpDir, "x.go"), true},
		{"absolute outside", "/etc/passwd", false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, inside := ResolveInWorkspace(tmpDir, tc.target)
			if inside != tc.inside {
				t.Errorf("target %q: expected inside=%v, got %v", tc.target, tc.inside, inside)
			}
		})
	}
}

// 验收 D4：工作区内指向外部的软链必须被判为越界
func TestResolveInWorkspace_SymlinkEscape(t *testing.T) {
	tmpDir := t.TempDir()

	// 1. 指向家目录敏感路径的软链
	evil := filepath.Join(tmpDir, "evil")
	if err := os.Symlink(t.TempDir(), evil); err != nil {
		t.Skip("symlink not supported")
	}
	if _, inside := ResolveInWorkspace(tmpDir, filepath.Join("evil", "pwn.txt")); inside {
		t.Errorf("symlink escape via ./evil/pwn.txt must be blocked")
	}

	// 2. 父目录为软链的新建路径（祖先 EvalSymlinks 生效）
	etcLink := filepath.Join(tmpDir, "etc-link")
	if err := os.Symlink("/etc", etcLink); err == nil {
		if _, inside := ResolveInWorkspace(tmpDir, filepath.Join("etc-link", "x")); inside {
			t.Errorf("symlink escape via ./etc-link/x must be blocked")
		}
	}

	// 3. 不存在的普通新建路径放行
	if _, inside := ResolveInWorkspace(tmpDir, filepath.Join("normal", "new.go")); !inside {
		t.Errorf("new file under normal dir must be allowed")
	}

	// 4. 工作区自身经软链访问（macOS /tmp → /private/tmp 场景）
	linkDir := filepath.Join(t.TempDir(), "link")
	if err := os.Symlink(tmpDir, linkDir); err == nil {
		if _, inside := ResolveInWorkspace(linkDir, "main.go"); !inside {
			t.Errorf("workDir accessed via symlink must still recognize its own children")
		}
	}
}

// ~/.tide 白名单保持
func TestResolveInWorkspace_TideHomeWhitelist(t *testing.T) {
	home, err := os.UserHomeDir()
	if err != nil {
		t.Skip("no home dir")
	}
	tidePath := filepath.Join(home, ".tide", "memory", "notes.md")
	_, inside := ResolveInWorkspace(t.TempDir(), tidePath)
	if !inside {
		t.Errorf("~/.tide paths must stay whitelisted, got outside")
	}
}
