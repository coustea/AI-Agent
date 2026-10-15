package builtin

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
)

// BashTool 执行系统 Shell 命令，学习自 learn-claude-code 中的 run_bash
type BashTool struct {
	workDir string
}

func NewBashTool(workDir ...string) *BashTool {
	wd := ""
	if len(workDir) > 0 {
		wd = workDir[0]
	}
	return &BashTool{workDir: wd}
}

func (t *BashTool) Name() string {
	return "bash"
}

func (t *BashTool) Description() string {
	return "Run a shell command."
}

func (t *BashTool) Schema() json.RawMessage {
	return json.RawMessage(`{
		"type": "object",
		"properties": {
			"command": {
				"type": "string",
				"description": "The shell command to execute"
			}
		},
		"required": ["command"]
	}`)
}

type BashInput struct {
	Command string `json:"command"`
}

const maxBashOutputBytes = 50000 // 学习自 learn-claude-code: output[:50000]

func (t *BashTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	var input BashInput
	if err := json.Unmarshal(args, &input); err != nil {
		return "", fmt.Errorf("failed to parse bash arguments: %w", err)
	}

	command := strings.TrimSpace(input.Command)
	if command == "" {
		return "", fmt.Errorf("command cannot be empty")
	}

	// 拦截高危指令（对齐 learn-claude-code）
	dangerous := []string{"rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"}
	for _, d := range dangerous {
		if strings.Contains(command, d) {
			return "", fmt.Errorf("dangerous command blocked: %s", d)
		}
	}

	cmd := exec.CommandContext(ctx, "bash", "-c", command)
	if t.workDir != "" {
		cmd.Dir = t.workDir
	}

	var combinedBuf bytes.Buffer
	cmd.Stdout = &combinedBuf
	cmd.Stderr = &combinedBuf

	err := cmd.Run()
	output := strings.TrimSpace(combinedBuf.String())

	// 截断超大输出
	if len(output) > maxBashOutputBytes {
		output = output[:maxBashOutputBytes] + "\n... (output truncated)"
	}

	if err != nil {
		if ctx.Err() != nil {
			return "", ctx.Err()
		}
		if output != "" {
			return "", fmt.Errorf("command failed (%w) with output:\n%s", err, output)
		}
		return "", fmt.Errorf("command failed: %w", err)
	}

	if output == "" {
		output = "(no output)"
	}

	return output, nil
}
