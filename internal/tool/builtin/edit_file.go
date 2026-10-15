package builtin

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

// EditFileTool 精确单次替换文件内的指定文本，学习自 learn-claude-code 中的 run_edit
type EditFileTool struct {
	workDir string
}

func NewEditFileTool(workDir ...string) *EditFileTool {
	wd := ""
	if len(workDir) > 0 {
		wd = workDir[0]
	}
	return &EditFileTool{workDir: wd}
}

func (t *EditFileTool) Name() string {
	return "edit_file"
}

func (t *EditFileTool) Description() string {
	return "Replace exact text in a file once."
}

func (t *EditFileTool) Schema() json.RawMessage {
	return json.RawMessage(`{
		"type": "object",
		"properties": {
			"path": {
				"type": "string",
				"description": "The path to the file to edit"
			},
			"old_text": {
				"type": "string",
				"description": "The exact text to find and replace"
			},
			"new_text": {
				"type": "string",
				"description": "The new replacement text"
			}
		},
		"required": ["path", "old_text", "new_text"]
	}`)
}

type EditFileInput struct {
	Path    string `json:"path"`
	OldText string `json:"old_text"`
	NewText string `json:"new_text"`
}

func (t *EditFileTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	var input EditFileInput
	if err := json.Unmarshal(args, &input); err != nil {
		return "", fmt.Errorf("failed to parse edit_file arguments: %w", err)
	}

	targetPath, err := SafePath(t.workDir, input.Path)
	if err != nil {
		return "", err
	}

	select {
	case <-ctx.Done():
		return "", ctx.Err()
	default:
	}

	data, err := os.ReadFile(targetPath)
	if err != nil {
		return "", fmt.Errorf("failed to read file %s: %w", input.Path, err)
	}

	content := string(data)
	if !strings.Contains(content, input.OldText) {
		return "", fmt.Errorf("text not found in %s", input.Path)
	}

	// 仅替换一次，确保修改的精确受控
	updated := strings.Replace(content, input.OldText, input.NewText, 1)

	if err := os.WriteFile(targetPath, []byte(updated), 0o644); err != nil {
		return "", fmt.Errorf("failed to write updated file %s: %w", input.Path, err)
	}

	return fmt.Sprintf("Edited %s", input.Path), nil
}
