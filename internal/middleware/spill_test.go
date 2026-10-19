package middleware

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"my-agent/pkg/llm"
)

// 验收 D10：大结果落盘行为与迁移前逐字节一致
func TestLargeResultSpill(t *testing.T) {
	dir := t.TempDir()
	hook := LargeResultSpill(dir)

	large := strings.Repeat("A", 9000)
	res := &llm.ToolResult{ToolCallID: "call_1", Content: large}
	hook(context.Background(), llm.ToolCall{ID: "call_1", Name: "bash"}, res)

	if !strings.Contains(res.Content, "[output truncated: 9000 characters total; full content saved to .tide/tool-results/call_1.txt") {
		t.Fatalf("unexpected spilled content: %s", res.Content)
	}

	saved, err := os.ReadFile(filepath.Join(dir, ".tide", "tool-results", "call_1.txt"))
	if err != nil {
		t.Fatalf("expected full result file: %v", err)
	}
	if string(saved) != large {
		t.Fatalf("saved content mismatch: %d bytes", len(saved))
	}

	// 小结果不改写
	small := &llm.ToolResult{ToolCallID: "call_2", Content: "ok"}
	hook(context.Background(), llm.ToolCall{ID: "call_2"}, small)
	if small.Content != "ok" {
		t.Errorf("small result must not be rewritten, got %q", small.Content)
	}

	// 同名冲突追加数字后缀
	dup := &llm.ToolResult{ToolCallID: "call_1", Content: large}
	hook(context.Background(), llm.ToolCall{ID: "call_1"}, dup)
	if _, err := os.Stat(filepath.Join(dir, ".tide", "tool-results", "call_1_1.txt")); err != nil {
		t.Errorf("expected deduplicated file call_1_1.txt: %v", err)
	}
}
