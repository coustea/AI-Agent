package files

import (
	"os"
	"path/filepath"
	"testing"
)

func TestWorkspaceOpenRejectsSymlink(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, "user", "conversation")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	outside := filepath.Join(t.TempDir(), "secret.txt")
	if err := os.WriteFile(outside, []byte("secret"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(dir, "link.txt")); err != nil {
		t.Fatal(err)
	}
	w := NewWorkspace(root)
	if f, _, err := w.Open("user", "conversation", "link.txt"); err == nil {
		f.Close()
		t.Fatal("不能打开指向工作区外的符号链接")
	}
	files, err := w.List("user", "conversation")
	if err != nil || len(files) != 0 {
		t.Fatalf("软链接不应出现在列表中: files=%v err=%v", files, err)
	}
}

// TestListHidesAttachmentsDir 附件目录不应出现在工作区文件列表里。
//
// 附件与工作区同根后，attachments/ 成了工作区的子目录。
// 它通过附件接口管理，混进产物列表会让用户看到两份语义重叠的条目。
func TestListHidesAttachmentsDir(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, "u1", "c1")
	if err := os.MkdirAll(filepath.Join(dir, "attachments"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "notes.md"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}

	files, err := NewWorkspace(root).List("u1", "c1")
	if err != nil {
		t.Fatal(err)
	}
	for _, f := range files {
		if f.Name == "attachments" {
			t.Fatal("附件目录不应出现在工作区文件列表里")
		}
	}
	if len(files) != 1 || files[0].Name != "notes.md" {
		t.Fatalf("files = %+v", files)
	}
}
