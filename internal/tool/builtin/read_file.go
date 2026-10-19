package builtin

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
)

// ReadFileTool 读取工作区内指定文件的文本内容，学习自 learn-claude-code 中的 run_read
type ReadFileTool struct {
	workDir *WorkDirRef
}

func NewReadFileTool(workDir *WorkDirRef) *ReadFileTool {
	return &ReadFileTool{workDir: workDir}
}

func (t *ReadFileTool) Name() string {
	return "read_file"
}

func (t *ReadFileTool) Description() string {
	return "Read file contents from the workspace. Use this to inspect source code, configuration files, documentation, or data files before modifying them or answering questions."
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

	targetPath, err := SafePath(t.workDir.Get(), input.Path)
	if err != nil {
		return "", err
	}

	file, err := os.Open(targetPath)
	if err != nil {
		return "", fmt.Errorf("failed to open file %s: %w", input.Path, err)
	}
	// 只读句柄：关闭失败无法补救，显式丢弃
	defer func() { _ = file.Close() }()

	// 逐行流式读取：ReadString 无单行长度上限（Scanner 有 64KB 限制），
	// limit 达到后立即停止，不再全量读入后截断。
	reader := bufio.NewReader(file)
	lines := make([]string, 0, 64)
	for {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		default:
		}

		line, readErr := reader.ReadString('\n')
		if line != "" {
			lines = append(lines, strings.TrimSuffix(strings.TrimSuffix(line, "\n"), "\r"))
		}

		if input.Limit > 0 && len(lines) >= input.Limit {
			// 探测是否还有后续内容（只多读一行，不累积），有则给出截断提示
			rest, peekErr := reader.ReadString('\n')
			if rest != "" || peekErr != io.EOF {
				lines = append(lines, fmt.Sprintf("... (truncated at %d lines)", input.Limit))
			}
			break
		}

		if readErr != nil {
			if readErr == io.EOF {
				break
			}
			return "", fmt.Errorf("error reading file %s: %w", input.Path, readErr)
		}
	}

	return strings.Join(lines, "\n"), nil
}
