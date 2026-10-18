package builtin

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// WriteFileTool 向工作区内的文件写入文本，学习自 learn-claude-code 中的 run_write
type WriteFileTool struct {
	workDir *WorkDirRef
}

func NewWriteFileTool(workDir *WorkDirRef) *WriteFileTool {
	return &WriteFileTool{workDir: workDir}
}

func (t *WriteFileTool) Name() string {
	return "write_file"
}

func (t *WriteFileTool) Description() string {
	return "Write complete content to a file in the workspace. Automatically creates any missing parent directories. Best for creating new files or completely rewriting existing files."
}

func (t *WriteFileTool) Schema() json.RawMessage {
	return json.RawMessage(`{
		"type": "object",
		"properties": {
			"path": {
				"type": "string",
				"description": "The path to the file to write"
			},
			"content": {
				"type": "string",
				"description": "The text content to write into the file"
			}
		},
		"required": ["path", "content"]
	}`)
}

type WriteFileInput struct {
	Path    string `json:"path"`
	Content string `json:"content"`
}

func (t *WriteFileTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	var input WriteFileInput
	if err := json.Unmarshal(args, &input); err != nil {
		return "", fmt.Errorf("failed to parse write_file arguments: %w", err)
	}

	targetPath, err := SafePath(t.workDir.Get(), input.Path)
	if err != nil {
		return "", err
	}

	select {
	case <-ctx.Done():
		return "", ctx.Err()
	default:
	}

	dir := filepath.Dir(targetPath)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", fmt.Errorf("failed to create parent directories for %s: %w", input.Path, err)
	}

	// 原子落盘：先写同目录临时文件再 Rename，避免中断留下半截文件
	tmp, err := os.CreateTemp(dir, ".tmp-*")
	if err != nil {
		return "", fmt.Errorf("failed to create temp file for %s: %w", input.Path, err)
	}
	tmpName := tmp.Name()

	if _, err := tmp.WriteString(input.Content); err != nil {
		_ = tmp.Close()
		_ = os.Remove(tmpName)
		return "", fmt.Errorf("failed to write file %s: %w", input.Path, err)
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmpName)
		return "", fmt.Errorf("failed to write file %s: %w", input.Path, err)
	}
	if err := os.Rename(tmpName, targetPath); err != nil {
		_ = os.Remove(tmpName)
		return "", fmt.Errorf("failed to write file %s: %w", input.Path, err)
	}

	return fmt.Sprintf("Wrote %d bytes to %s", len(input.Content), input.Path), nil
}
