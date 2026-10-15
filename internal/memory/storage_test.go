package memory

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestStorage_Dirs(t *testing.T) {
	globalDir := GlobalDir()
	if !filepath.IsAbs(globalDir) {
		t.Errorf("expected globalDir to be absolute, got %s", globalDir)
	}
	if !strings.HasSuffix(globalDir, filepath.Join(".coustea", "memory")) {
		t.Errorf("expected globalDir to end with .coustea/memory, got %s", globalDir)
	}

	workDir := "/Users/test/workspace"
	projDir := ProjectDir(workDir)
	expectedProj := filepath.Join(workDir, ".coustea", "memory")
	if projDir != expectedProj {
		t.Errorf("expected %s, got %s", expectedProj, projDir)
	}
}

func TestStorage_LoadAndFormatBundle(t *testing.T) {
	tmpDir := t.TempDir()
	customGlobalDir := filepath.Join(tmpDir, "global_mem")

	// 1. 测试空工作区时的默认说明
	emptyBundle := LoadBundle(tmpDir, customGlobalDir)
	if emptyBundle.HasContent() {
		t.Errorf("expected empty bundle to have no content")
	}
	prompt := emptyBundle.FormatForPrompt()
	if !strings.Contains(prompt, "Long-Term Memory") {
		t.Errorf("expected prompt to contain Long-Term Memory, got:\n%s", prompt)
	}
	if !strings.Contains(prompt, "当前尚未记录长期记忆") {
		t.Errorf("expected prompt to indicate no content yet, got:\n%s", prompt)
	}

	// 2. 写入项目特定记忆
	projectMemDir := filepath.Join(tmpDir, ".coustea", "memory")
	if err := os.MkdirAll(projectMemDir, 0o755); err != nil {
		t.Fatalf("failed to create project mem dir: %v", err)
	}

	projFile := filepath.Join(projectMemDir, FileProject)
	projContent := "# Workspace Info\nGoal: build a general-purpose AI assistant."
	if err := os.WriteFile(projFile, []byte(projContent), 0o644); err != nil {
		t.Fatalf("failed to write project.md: %v", err)
	}

	prefFile := filepath.Join(projectMemDir, FilePreferences)
	prefContent := "Language: Chinese\nTone: Professional"
	if err := os.WriteFile(prefFile, []byte(prefContent), 0o644); err != nil {
		t.Fatalf("failed to write preferences.md: %v", err)
	}

	// 重新加载 bundle
	bundle := LoadBundle(tmpDir, customGlobalDir)
	if !bundle.HasContent() {
		t.Errorf("expected bundle to have content")
	}

	formatted := bundle.FormatForPrompt()
	if !strings.Contains(formatted, "Workspace Info") {
		t.Errorf("expected formatted prompt to contain project content:\n%s", formatted)
	}
	if !strings.Contains(formatted, "Goal: build a general-purpose AI assistant") {
		t.Errorf("expected formatted prompt to contain goal:\n%s", formatted)
	}
	if !strings.Contains(formatted, "Language: Chinese") {
		t.Errorf("expected formatted prompt to contain preferences:\n%s", formatted)
	}
}

func TestStorage_EnsureDirsAndTemplates(t *testing.T) {
	tmpDir := t.TempDir()
	customGlobalDir := filepath.Join(tmpDir, "global_mem")

	if err := EnsureDirs(tmpDir, customGlobalDir); err != nil {
		t.Fatalf("EnsureDirs failed: %v", err)
	}

	projMemDir := ProjectDir(tmpDir)
	if fi, err := os.Stat(projMemDir); err != nil || !fi.IsDir() {
		t.Errorf("expected project memory dir to exist as a directory: %v", err)
	}

	// 测试初始化模板
	if err := InitTemplates(tmpDir, customGlobalDir); err != nil {
		t.Fatalf("InitTemplates failed: %v", err)
	}

	projFile := filepath.Join(projMemDir, FileProject)
	data, err := os.ReadFile(projFile)
	if err != nil {
		t.Fatalf("failed to read created project template: %v", err)
	}
	if !strings.Contains(string(data), "coustea 通用个人本地 AI 智能助手") {
		t.Errorf("unexpected project template content: %s", string(data))
	}
}
