package builtin

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

// ReadFileTool 读取工作区内指定文件的文本内容，学习自 learn-claude-code 中的 run_read
type ReadFileTool struct {
	workDir string
}

func NewReadFileTool(workDir ...string) *ReadFileTool {
	wd := ""
	if len(workDir) > 0 {
		wd = workDir[0]
	}
	return &ReadFileTool{workDir: wd}
}

func (t *ReadFileTool) Name() string {
	return "read_file"
}

func (t *ReadFileTool) Description() string {
	return "Read file contents from the workspace."
}

func (t *ReadFileTool) Schema() json.RawMessage {
	return json.RawMessage(`{
		"type": "object",
		"properties": {
			"path": {
				"type": "string",
				"description": "The relative or absolute path of the file to read"
			},
			"limit": {
				"type": "integer",
				"description": "Optional maximum number of lines to read"
			}
		},
		"required": ["path"]
	}`)
}

type ReadFileInput struct {
	Path  string `json:"path"`
	Limit int    `json:"limit,omitempty"`
}

func (t *ReadFileTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	var input ReadFileInput
	if err := json.Unmarshal(args, &input); err != nil {
		return "", fmt.Errorf("failed to parse read_file arguments: %w", err)
	}

	targetPath, err := SafePath(t.workDir, input.Path)
	if err != nil {
		return "", err
	}

	file, err := os.Open(targetPath)
	if err != nil {
		return "", fmt.Errorf("failed to open file %s: %w", input.Path, err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	var lines []string

	for scanner.Scan() {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		default:
		}
		lines = append(lines, scanner.Text())
	}

	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("error reading file %s: %w", input.Path, err)
	}

	if input.Limit > 0 && input.Limit < len(lines) {
		remaining := len(lines) - input.Limit
		lines = append(lines[:input.Limit], fmt.Sprintf("... (%d more lines)", remaining))
	}

	return strings.Join(lines, "\n"), nil
}
