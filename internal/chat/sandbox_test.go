package chat

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	adkfs "github.com/cloudwego/eino/adk/filesystem"
)

// newTestSandbox 构造一个三挂载点都指向临时目录的沙箱。
func newTestSandbox(t *testing.T) (*Sandbox, string, string, string) {
	t.Helper()

	base := t.TempDir()
	ws := filepath.Join(base, "workspace")
	off := filepath.Join(base, "offload")
	sk := filepath.Join(base, "skills")

	if err := os.MkdirAll(sk, 0o755); err != nil {
		t.Fatalf("创建技能目录: %v", err)
	}

	sb, err := NewSandbox(ws, off, sk)
	if err != nil {
		t.Fatalf("NewSandbox: %v", err)
	}
	return sb, ws, off, sk
}

// TestSandboxWriteReadWorkspace 验证 /workspace 可读写且落盘到正确目录。
func TestSandboxWriteReadWorkspace(t *testing.T) {
	sb, ws, _, _ := newTestSandbox(t)
	ctx := context.Background()

	if err := sb.Write(ctx, &adkfs.WriteRequest{
		FilePath: MountWorkspace + "/notes.md",
		Content:  "第一行\n第二行",
	}); err != nil {
		t.Fatalf("写入失败: %v", err)
	}

	// 确认真的落到宿主机工作目录
	onDisk := filepath.Join(ws, "notes.md")
	data, err := os.ReadFile(onDisk)
	if err != nil {
		t.Fatalf("文件未落盘: %v", err)
	}
	if string(data) != "第一行\n第二行" {
		t.Errorf("内容不符: %q", data)
	}

	got, err := sb.Read(ctx, &adkfs.ReadRequest{FilePath: MountWorkspace + "/notes.md"})
	if err != nil {
		t.Fatalf("读取失败: %v", err)
	}
	if got.Content != "第一行\n第二行" {
		t.Errorf("读回内容不符: %q", got.Content)
	}
}

// TestSandboxReadOffsetLimit 验证按行读取。
func TestSandboxReadOffsetLimit(t *testing.T) {
	sb, _, _, _ := newTestSandbox(t)
	ctx := context.Background()

	content := "l1\nl2\nl3\nl4\nl5"
	if err := sb.Write(ctx, &adkfs.WriteRequest{
		FilePath: MountWorkspace + "/lines.txt", Content: content,
	}); err != nil {
		t.Fatalf("写入失败: %v", err)
	}

	got, err := sb.Read(ctx, &adkfs.ReadRequest{
		FilePath: MountWorkspace + "/lines.txt",
		Offset:   2,
		Limit:    2,
	})
	if err != nil {
		t.Fatalf("读取失败: %v", err)
	}
	if got.Content != "l2\nl3" {
		t.Errorf("按行读取结果不符: %q", got.Content)
	}
}

// TestSandboxRejectsTraversal 验证 ../ 逃逸被拒绝。
func TestSandboxRejectsTraversal(t *testing.T) {
	sb, _, _, _ := newTestSandbox(t)
	ctx := context.Background()

	cases := []string{
		MountWorkspace + "/../../../etc/passwd",
		MountWorkspace + "/../secret",
		"/../etc/passwd",
	}

	for _, p := range cases {
		got, err := sb.Read(ctx, &adkfs.ReadRequest{FilePath: p})
		if err != nil {
			continue // 返回 error 也算是拒绝
		}
		// 沙箱把拒绝表达为说明文本而非 error（这样模型能自行纠正），
		// 关键断言是：绝不能返回沙箱外文件的真实内容。
		if !strings.Contains(got.Content, "拒绝") {
			t.Errorf("路径 %q 应被拒绝，实际返回 %q", p, got.Content)
		}
	}
}

// TestSandboxRejectsUnknownMount 验证沙箱外路径一律拒绝。
func TestSandboxRejectsUnknownMount(t *testing.T) {
	sb, _, _, _ := newTestSandbox(t)
	ctx := context.Background()

	cases := []string{"/etc/passwd", "/root/.ssh/id_rsa", "/tmp/x", "/workspaces/x"}

	for _, p := range cases {
		got, err := sb.Read(ctx, &adkfs.ReadRequest{FilePath: p})
		if err != nil {
			continue
		}
		if !strings.Contains(got.Content, "拒绝") {
			t.Errorf("沙箱外路径 %q 应被拒绝，实际返回 %q", p, got.Content)
		}
	}
}

// TestSandboxSkillsReadOnly 验证 /skills 可读、不可写。
func TestSandboxSkillsReadOnly(t *testing.T) {
	sb, _, _, sk := newTestSandbox(t)
	ctx := context.Background()

	// 预置一个技能文件
	skillFile := filepath.Join(sk, "demo", "SKILL.md")
	if err := os.MkdirAll(filepath.Dir(skillFile), 0o755); err != nil {
		t.Fatalf("创建技能目录: %v", err)
	}
	if err := os.WriteFile(skillFile, []byte("# Demo Skill"), 0o644); err != nil {
		t.Fatalf("写入技能文件: %v", err)
	}

	// 读应当成功
	got, err := sb.Read(ctx, &adkfs.ReadRequest{FilePath: MountSkills + "/demo/SKILL.md"})
	if err != nil {
		t.Fatalf("读取技能应成功: %v", err)
	}
	if !strings.Contains(got.Content, "Demo Skill") {
		t.Errorf("技能内容不符: %q", got.Content)
	}

	// 写应当失败
	err = sb.Write(ctx, &adkfs.WriteRequest{
		FilePath: MountSkills + "/demo/SKILL.md", Content: "被篡改",
	})
	if err == nil {
		t.Fatal("对只读挂载点的写入应被拒绝")
	}
	if !errors.Is(err, ErrReadOnly) {
		t.Errorf("应返回 ErrReadOnly，实际 %v", err)
	}
}

// TestSandboxRejectsSymlinkEscape 验证符号链接逃逸被拒绝。
func TestSandboxRejectsSymlinkEscape(t *testing.T) {
	sb, ws, _, _ := newTestSandbox(t)
	ctx := context.Background()

	// 在工作区内创建一个指向工作区外的软链接
	outside := t.TempDir()
	secret := filepath.Join(outside, "secret.txt")
	if err := os.WriteFile(secret, []byte("机密"), 0o644); err != nil {
		t.Fatalf("准备外部文件: %v", err)
	}

	link := filepath.Join(ws, "escape")
	if err := os.Symlink(outside, link); err != nil {
		t.Skipf("创建软链接失败（可能无权限）: %v", err)
	}

	// 软链接逃逸必须被拦住：无论返回 error 还是说明文本，
	// 都不能返回外部文件的真实内容「机密」。
	got, err := sb.Read(ctx, &adkfs.ReadRequest{FilePath: MountWorkspace + "/escape/secret.txt"})
	if err == nil && strings.Contains(got.Content, "机密") {
		t.Fatal("软链接逃逸泄露了沙箱外文件内容")
	}
}

// TestSandboxOffloadMount 验证 /.offload 可读写。
func TestSandboxOffloadMount(t *testing.T) {
	sb, _, off, _ := newTestSandbox(t)
	ctx := context.Background()

	if err := sb.Write(ctx, &adkfs.WriteRequest{
		FilePath: MountOffload + "/trunc/abc", Content: "大结果",
	}); err != nil {
		t.Fatalf("写入 offload 失败: %v", err)
	}

	if _, err := os.Stat(filepath.Join(off, "trunc", "abc")); err != nil {
		t.Errorf("offload 文件未落盘: %v", err)
	}
}

// TestSandboxEdit 验证精确替换与多匹配保护。
func TestSandboxEdit(t *testing.T) {
	sb, _, _, _ := newTestSandbox(t)
	ctx := context.Background()

	path := MountWorkspace + "/edit.txt"
	if err := sb.Write(ctx, &adkfs.WriteRequest{FilePath: path, Content: "foo bar foo"}); err != nil {
		t.Fatalf("写入失败: %v", err)
	}

	// 多处匹配且未开启 ReplaceAll：应报错
	err := sb.Edit(ctx, &adkfs.EditRequest{FilePath: path, OldString: "foo", NewString: "baz"})
	if err == nil {
		t.Fatal("多处匹配应要求 replace_all")
	}

	// 开启 ReplaceAll 后成功
	if err := sb.Edit(ctx, &adkfs.EditRequest{
		FilePath: path, OldString: "foo", NewString: "baz", ReplaceAll: true,
	}); err != nil {
		t.Fatalf("replace_all 替换失败: %v", err)
	}

	got, _ := sb.Read(ctx, &adkfs.ReadRequest{FilePath: path})
	if got.Content != "baz bar baz" {
		t.Errorf("替换结果不符: %q", got.Content)
	}

	// 空 old_string 应报错
	if err := sb.Edit(ctx, &adkfs.EditRequest{FilePath: path, OldString: ""}); err == nil {
		t.Error("空 old_string 应报错")
	}
}

// TestSandboxLsInfo 验证列目录。
func TestSandboxLsInfo(t *testing.T) {
	sb, _, _, _ := newTestSandbox(t)
	ctx := context.Background()

	for _, name := range []string{"a.txt", "b.txt"} {
		if err := sb.Write(ctx, &adkfs.WriteRequest{
			FilePath: MountWorkspace + "/" + name, Content: "x",
		}); err != nil {
			t.Fatalf("写入 %s: %v", name, err)
		}
	}

	infos, err := sb.LsInfo(ctx, &adkfs.LsInfoRequest{Path: MountWorkspace})
	if err != nil {
		t.Fatalf("LsInfo: %v", err)
	}
	if len(infos) < 2 {
		t.Errorf("应列出至少 2 个文件，实际 %d", len(infos))
	}
}

// TestSandboxGrep 验证按正则搜索。
func TestSandboxGrep(t *testing.T) {
	sb, _, _, _ := newTestSandbox(t)
	ctx := context.Background()

	if err := sb.Write(ctx, &adkfs.WriteRequest{
		FilePath: MountWorkspace + "/code.go",
		Content:  "package main\n\nfunc hello() {}\n",
	}); err != nil {
		t.Fatalf("写入失败: %v", err)
	}

	matches, err := sb.GrepRaw(ctx, &adkfs.GrepRequest{
		Pattern: "func \\w+", Path: MountWorkspace,
	})
	if err != nil {
		t.Fatalf("GrepRaw: %v", err)
	}
	if len(matches) != 1 {
		t.Fatalf("应匹配 1 行，实际 %d", len(matches))
	}
	if matches[0].Line != 3 {
		t.Errorf("行号应为 3，实际 %d", matches[0].Line)
	}
}

// TestSandboxGlob 验证 glob 匹配。
func TestSandboxGlob(t *testing.T) {
	sb, _, _, _ := newTestSandbox(t)
	ctx := context.Background()

	for _, name := range []string{"a.md", "b.md", "c.txt"} {
		if err := sb.Write(ctx, &adkfs.WriteRequest{
			FilePath: MountWorkspace + "/" + name, Content: "x",
		}); err != nil {
			t.Fatalf("写入 %s: %v", name, err)
		}
	}

	infos, err := sb.GlobInfo(ctx, &adkfs.GlobInfoRequest{
		Pattern: "*.md", Path: MountWorkspace,
	})
	if err != nil {
		t.Fatalf("GlobInfo: %v", err)
	}
	if len(infos) != 2 {
		t.Errorf("应匹配 2 个 md 文件，实际 %d", len(infos))
	}
}
