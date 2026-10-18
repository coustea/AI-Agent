package builtin

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"my-agent/internal/textutil"
)

// bash 超时边界：默认 120s，模型可按需覆盖，夹取到 [100ms, 10min]
const (
	defaultBashTimeoutMs = 120_000
	minBashTimeoutMs     = 100
	maxBashTimeoutMs     = 600_000
)

// BashTool 执行系统 Shell 命令，学习自 learn-claude-code 中的 run_bash。
//
// 本工具是纯执行器：不含任何安全策略。命令是否允许执行由
// 三道闸门权限管线统一裁决（见 internal/permission）。
type BashTool struct {
	workDir *WorkDirRef
}

func NewBashTool(workDir *WorkDirRef) *BashTool {
	return &BashTool{workDir: workDir}
}

func (t *BashTool) Name() string {
	return "bash"
}

func (t *BashTool) Description() string {
	return "Execute a non-interactive shell command on the host system. Use this to run CLI utilities, system diagnostics, code builds/tests, git operations, and query remote APIs or public web services (e.g. via curl)."
}

func (t *BashTool) Schema() json.RawMessage {
	return json.RawMessage(`{
		"type": "object",
		"properties": {
			"command": {
				"type": "string",
				"description": "The shell command to execute"
			},
			"timeout_ms": {
				"type": "integer",
				"description": "Optional timeout in milliseconds. Default 120000 (120s), max 600000 (10min). Set a larger value for long-running builds or tests."
			}
		},
		"required": ["command"]
	}`)
}

type BashInput struct {
	Command   string `json:"command"`
	TimeoutMs *int64 `json:"timeout_ms,omitempty"`
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

	var timeoutMs int64 = defaultBashTimeoutMs
	if input.TimeoutMs != nil && *input.TimeoutMs > 0 {
		timeoutMs = *input.TimeoutMs
	}
	if timeoutMs < minBashTimeoutMs {
		timeoutMs = minBashTimeoutMs
	}
	if timeoutMs > maxBashTimeoutMs {
		timeoutMs = maxBashTimeoutMs
	}

	cmdCtx, cancel := context.WithTimeout(ctx, time.Duration(timeoutMs)*time.Millisecond)
	defer cancel()

	cmd := createShellCmd(cmdCtx, command)
	setupProcessGroup(cmd)
	cmd.Dir = t.workDir.Get()

	var combinedBuf bytes.Buffer
	cmd.Stdout = &combinedBuf
	cmd.Stderr = &combinedBuf

	err := cmd.Run()
	output := strings.TrimSpace(combinedBuf.String())

	// 截断超大输出（按 UTF-8 字符边界，避免切断多字节字符）
	if len(output) > maxBashOutputBytes {
		output = textutil.TruncateUTF8(output, maxBashOutputBytes) + "\n... (output truncated)"
	}

	if err != nil {
		if cmdCtx.Err() == context.DeadlineExceeded {
			if len(output) > maxBashOutputBytes {
				output = textutil.TruncateUTF8(output, maxBashOutputBytes)
			}
			if output != "" {
				return "", fmt.Errorf("bash: command timed out after %dms with output:\n%s", timeoutMs, output)
			}
			return "", fmt.Errorf("bash: command timed out after %dms", timeoutMs)
		}
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
