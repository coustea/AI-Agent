package builtin

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestSafePath(t *testing.T) {
	tmpDir := t.TempDir()

	// 1. 正常工作区内部路径
	p, err := SafePath(tmpDir, "file.txt")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := filepath.Join(tmpDir, "file.txt")
	if p != expected {
		t.Errorf("expected %s, got %s", expected, p)
	}

	// 2. 子目录路径
	p, err = SafePath(tmpDir, "sub/dir/nested.txt")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected = filepath.Join(tmpDir, "sub/dir/nested.txt")
	if p != expected {
		t.Errorf("expected %s, got %s", expected, p)
	}

	// 3. 越界逃逸路径（必须被安全拦截）
	_, err = SafePath(tmpDir, "../../etc/passwd")
	if err == nil {
		t.Errorf("expected error for escaping path, got nil")
	}

	// 4. 空路径拦截
	_, err = SafePath(tmpDir, "   ")
	if err == nil {
		t.Errorf("expected error for empty path, got nil")
	}

	// 5. 允许访问全局记忆与配置目录 (~/.tide)
	home, _ := os.UserHomeDir()
	if home != "" {
		globalTidePath := filepath.Join(home, ".tide", "memory", "preferences.md")
		p, err := SafePath(tmpDir, globalTidePath)
		if err != nil {
			t.Errorf("expected access to ~/.tide to be allowed, got error: %v", err)
		}
		if p != globalTidePath {
			t.Errorf("expected %s, got %s", globalTidePath, p)
		}
	}
}

func TestReadFileTool(t *testing.T) {
	tmpDir := t.TempDir()
	testFile := "sample.txt"
	content := "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
	if err := os.WriteFile(filepath.Join(tmpDir, testFile), []byte(content), 0644); err != nil {
		t.Fatalf("failed to write test file: %v", err)
	}

	tool := NewReadFileTool(tmpDir)

	// 1. 全量读取
	args, _ := json.Marshal(ReadFileInput{Path: testFile})
	out, err := tool.Execute(context.Background(), args)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(out, "Line 1") || !strings.Contains(out, "Line 5") {
		t.Errorf("unexpected output: %s", out)
	}

	// 2. 限制行数读取 (limit=2)
	argsLimit, _ := json.Marshal(ReadFileInput{Path: testFile, Limit: 2})
	outLimit, err := tool.Execute(context.Background(), argsLimit)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(outLimit, "Line 1") || !strings.Contains(outLimit, "Line 2") {
		t.Errorf("expected first two lines: %s", outLimit)
	}
	if strings.Contains(outLimit, "Line 3") {
		t.Errorf("output should not contain line 3: %s", outLimit)
	}
	if !strings.Contains(outLimit, "(3 more lines)") {
		t.Errorf("expected remaining lines count summary, got: %s", outLimit)
	}

	// 3. 文件不存在报错
	argsNotFound, _ := json.Marshal(ReadFileInput{Path: "missing.txt"})
	_, err = tool.Execute(context.Background(), argsNotFound)
	if err == nil {
		t.Errorf("expected error for missing file, got nil")
	}

	// 4. 越界读取拦截
	argsEscape, _ := json.Marshal(ReadFileInput{Path: "../escaped.txt"})
	_, err = tool.Execute(context.Background(), argsEscape)
	if err == nil {
		t.Errorf("expected path escape error, got nil")
	}
}

func TestWriteFileTool(t *testing.T) {
	tmpDir := t.TempDir()
	tool := NewWriteFileTool(tmpDir)

	// 1. 自动递归创建父目录并写入文件
	target := "nested/sub/hello.txt"
	content := "Hello from write_file tool!"
	args, _ := json.Marshal(WriteFileInput{Path: target, Content: content})
	out, err := tool.Execute(context.Background(), args)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(out, "Wrote") || !strings.Contains(out, target) {
		t.Errorf("unexpected output: %s", out)
	}

	// 校验磁盘文件内容
	readBack, err := os.ReadFile(filepath.Join(tmpDir, target))
	if err != nil {
		t.Fatalf("failed to read back written file: %v", err)
	}
	if string(readBack) != content {
		t.Errorf("file content mismatch: expected %q, got %q", content, string(readBack))
	}

	// 2. 越界写入拦截
	argsEscape, _ := json.Marshal(WriteFileInput{Path: "../hacked.txt", Content: "bad"})
	_, err = tool.Execute(context.Background(), argsEscape)
	if err == nil {
		t.Errorf("expected escape error, got nil")
	}
}

func TestEditFileTool(t *testing.T) {
	tmpDir := t.TempDir()
	testFile := "edit_sample.txt"
	initialContent := "func main() {\n\tfmt.Println(\"Old Message\")\n\tfmt.Println(\"Old Message\")\n}"
	_ = os.WriteFile(filepath.Join(tmpDir, testFile), []byte(initialContent), 0644)

	tool := NewEditFileTool(tmpDir)

	// 1. 精确单次替换
	args, _ := json.Marshal(EditFileInput{
		Path:    testFile,
		OldText: "Old Message",
		NewText: "New Message",
	})
	out, err := tool.Execute(context.Background(), args)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(out, "Edited") {
		t.Errorf("unexpected output: %s", out)
	}

	// 验证只替换了第一次出现的 OldText
	updatedBytes, _ := os.ReadFile(filepath.Join(tmpDir, testFile))
	updated := string(updatedBytes)
	if !strings.Contains(updated, "New Message") {
		t.Errorf("New Message not found: %s", updated)
	}
	if !strings.Contains(updated, "Old Message") {
		t.Errorf("Second occurrence should have remained Old Message: %s", updated)
	}

	// 2. 查找文本不存在时报错
	argsNotFound, _ := json.Marshal(EditFileInput{
		Path:    testFile,
		OldText: "Nonexistent text",
		NewText: "Won't happen",
	})
	_, err = tool.Execute(context.Background(), argsNotFound)
	if err == nil {
		t.Errorf("expected error for nonexistent text")
	}
}

func TestGlobTool(t *testing.T) {
	tmpDir := t.TempDir()
	_ = os.MkdirAll(filepath.Join(tmpDir, "src", "pkg"), 0755)
	_ = os.WriteFile(filepath.Join(tmpDir, "root.go"), []byte("package main"), 0644)
	_ = os.WriteFile(filepath.Join(tmpDir, "README.md"), []byte("# Hello"), 0644)
	_ = os.WriteFile(filepath.Join(tmpDir, "src", "main.go"), []byte("package main"), 0644)
	_ = os.WriteFile(filepath.Join(tmpDir, "src", "pkg", "lib.go"), []byte("package pkg"), 0644)
	_ = os.WriteFile(filepath.Join(tmpDir, "src", "pkg", "lib_test.go"), []byte("package pkg"), 0644)

	tool := NewGlobTool(tmpDir)

	// 1. 递归匹配所有 .go 文件 (**/*.go)
	argsRec, _ := json.Marshal(GlobInput{Pattern: "**/*.go"})
	outRec, err := tool.Execute(context.Background(), argsRec)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(outRec, "root.go") ||
		!strings.Contains(outRec, "src/main.go") ||
		!strings.Contains(outRec, "src/pkg/lib.go") ||
		!strings.Contains(outRec, "src/pkg/lib_test.go") {
		t.Errorf("recursive glob failed to match all files:\n%s", outRec)
	}
	if strings.Contains(outRec, "README.md") {
		t.Errorf("glob should not match README.md: %s", outRec)
	}

	// 2. 单层通配 (*.go)
	argsTop, _ := json.Marshal(GlobInput{Pattern: "*.go"})
	outTop, err := tool.Execute(context.Background(), argsTop)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(outTop, "root.go") {
		t.Errorf("top-level glob failed to match root.go: %s", outTop)
	}
	if strings.Contains(outTop, "src/") {
		t.Errorf("top-level glob should not match subdirectories: %s", outTop)
	}

	// 3. 无匹配项
	argsNone, _ := json.Marshal(GlobInput{Pattern: "*.rust"})
	outNone, err := tool.Execute(context.Background(), argsNone)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if outNone != "(no matches)" {
		t.Errorf("expected (no matches), got: %q", outNone)
	}
}

func TestBashTool(t *testing.T) {
	tmpDir := t.TempDir()
	tool := NewBashTool(tmpDir)

	// 1. 正常执行
	args, _ := json.Marshal(BashInput{Command: "echo 'Coustea Test'"})
	out, err := tool.Execute(context.Background(), args)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out != "Coustea Test" {
		t.Errorf("unexpected output: %q", out)
	}

	// 2. 纯执行器：工具内不再包含任何安全策略
	//    （命令是否放行由 Harness 权限管线决定，见 internal/permission）
	argsPolicyFree, _ := json.Marshal(BashInput{Command: "echo sudo shutdown"})
	outPolicyFree, err := tool.Execute(context.Background(), argsPolicyFree)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if outPolicyFree != "sudo shutdown" {
		t.Errorf("bash tool should execute policy-free commands verbatim, got %q", outPolicyFree)
	}

	// 3. 执行报错
	argsFail, _ := json.Marshal(BashInput{Command: "exit 42"})
	_, err = tool.Execute(context.Background(), argsFail)
	if err == nil {
		t.Errorf("expected error for non-zero exit code")
	}

	// 4. 超时控制
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	argsTimeout, _ := json.Marshal(BashInput{Command: "sleep 1"})
	_, err = tool.Execute(ctx, argsTimeout)
	if err == nil {
		t.Errorf("expected timeout error")
	}

	// 5. 进程组取消杀死测试 (防止子进程孤儿化)
	ctxCancel, cancelFn := context.WithCancel(context.Background())
	argsSleep, _ := json.Marshal(BashInput{Command: "sh -c 'sleep 10'"})
	start := time.Now()
	go func() {
		time.Sleep(30 * time.Millisecond)
		cancelFn()
	}()
	_, err = tool.Execute(ctxCancel, argsSleep)
	if err == nil {
		t.Errorf("expected error when context canceled")
	}
	if time.Since(start) > 2*time.Second {
		t.Errorf("expected bash to terminate promptly on cancel, took %v", time.Since(start))
	}
}

func TestGrepTool(t *testing.T) {
	tmpDir := t.TempDir()

	_ = os.WriteFile(filepath.Join(tmpDir, "file1.go"), []byte("package main\n\nfunc Hello() string {\n\treturn \"coustea\"\n}\n"), 0o644)
	_ = os.WriteFile(filepath.Join(tmpDir, "file2.txt"), []byte("Hello coustea personal agent!\nLine 2 without keyword\nAnother coustea match\n"), 0o644)
	_ = os.MkdirAll(filepath.Join(tmpDir, "sub"), 0o755)
	_ = os.WriteFile(filepath.Join(tmpDir, "sub", "sub.go"), []byte("package sub\n\nfunc TargetFunc() {}\n"), 0o644)

	tool := NewGrepTool(tmpDir)

	// 1. 全局检索模式
	args1, _ := json.Marshal(GrepInput{Pattern: `coustea`})
	out1, err := tool.Execute(context.Background(), args1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(out1, "file1.go:4:") || !strings.Contains(out1, "file2.txt:1:") || !strings.Contains(out1, "file2.txt:3:") {
		t.Errorf("expected multiple matches across files, got:\n%s", out1)
	}

	// 2. 带 include 通配过滤检索
	args2, _ := json.Marshal(GrepInput{Pattern: `coustea`, Include: "*.go"})
	out2, err := tool.Execute(context.Background(), args2)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(out2, "file1.go:4:") {
		t.Errorf("expected match in file1.go, got: %s", out2)
	}
	if strings.Contains(out2, "file2.txt") {
		t.Errorf("file2.txt should be excluded by include filter, got: %s", out2)
	}

	// 3. 最大匹配数截断
	args3, _ := json.Marshal(GrepInput{Pattern: `coustea`, MaxResults: 1})
	out3, err := tool.Execute(context.Background(), args3)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(out3, "limit of 1 results reached") {
		t.Errorf("expected truncation notice for max_results=1, got:\n%s", out3)
	}

	// 4. 无匹配项
	args4, _ := json.Marshal(GrepInput{Pattern: `NonExistentPattern12345`})
	out4, err := tool.Execute(context.Background(), args4)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out4 != "(no matches)" {
		t.Errorf("expected '(no matches)', got: %q", out4)
	}

	// 5. 路径逃逸安全拦截
	args5, _ := json.Marshal(GrepInput{Pattern: `coustea`, Path: "../../escaped"})
	_, err = tool.Execute(context.Background(), args5)
	if err == nil {
		t.Errorf("expected error for escaping path")
	}
}
