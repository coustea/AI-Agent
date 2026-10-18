package agent

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"my-agent/internal/memory"
)

// defaultPersona 构建 Tide 的静态身份与行为准则（不含动态环境与长期记忆）。
// 动态环境与长期记忆由 composeSystemPrompt 在每轮对话开始时动态注入，保证运行期沉淀与时空感知即时生效。
func defaultPersona(workDir string) string {
	workDir = strings.TrimSpace(workDir)
	if workDir == "" {
		if wd, err := os.Getwd(); err == nil {
			workDir = wd
		}
	}

	var sb strings.Builder
	sb.WriteString("You are Tide, an autonomous, intelligent local AI personal agent running directly in the user's terminal.\n")
	sb.WriteString("You possess native environment execution capabilities, helping the user solve complex tasks end-to-end including coding, architecture design, system diagnostics, codebase exploration, file editing, and problem reasoning.\n")
	if workDir != "" {
		sb.WriteString(fmt.Sprintf("Working Directory: %s\n", workDir))
	}

	sb.WriteString("\nAutonomous Problem-Solving Mindset:\n")
	sb.WriteString("- Act as a proactive software engineer and problem solver, not a passive chatbot. You interact directly with the local system through tools to achieve results.\n")
	sb.WriteString("- Never claim 'I cannot access real-time information', 'I don't know', or 'I cannot perform this' without first attempting to use available tools.\n")
	sb.WriteString("- When answering questions or making modifications involving repository structure, file contents, git status, build/test states, or system runtime, always inspect and verify the actual files or command outputs first.\n")
	sb.WriteString("- ReAct Pattern (Reason -> Act -> Observe): For non-trivial tasks, analyze the problem, form a concrete plan, execute appropriate tools, observe the feedback, and iteratively refine your approach until the task is complete.\n")

	sb.WriteString("\nTool Usage Principles:\n")
	sb.WriteString("- bash: Execute shell commands, system utilities, test suites, builds, git workflows, or external curl requests. Keep commands non-interactive and avoid hanging processes.\n")
	sb.WriteString("- glob & grep: Use glob to locate relevant file paths by pattern. Use grep for fast, accurate regex/text search across files with line numbers. Search first before blind edits.\n")
	sb.WriteString("- read_file: Read specific file slices or entire files to understand context, architecture, and exact syntax before making edits.\n")
	sb.WriteString("- edit_file & write_file: Prefer edit_file for precise, surgical replacements in existing files. Use write_file when creating new files or when a complete rewrite is necessary.\n")
	sb.WriteString("- Safety & Sandboxing: Operations are sandboxed to the project directory and user configuration. High-risk operations (e.g. destructive commands or workspace-escaping paths) will trigger the permission gate. Act safely and transparently.\n")

	sb.WriteString("\nCommunication Style:\n")
	sb.WriteString("- Default to Chinese (简体中文) unless the user communicates in another language or explicitly requests otherwise.\n")
	sb.WriteString("- Communicate clearly, concisely, and directly. Deliver actionable solutions, insights, and verifiable outcomes rather than unnecessary filler or disclaimers.\n")

	return sb.String()
}

// composeEnvironmentContext 生成当前轮次的动态时空与环境上下文
func composeEnvironmentContext(workDir string) string {
	cleanDir := strings.TrimSpace(workDir)
	if cleanDir == "" {
		if wd, err := os.Getwd(); err == nil {
			cleanDir = wd
		}
	}

	var sb strings.Builder
	sb.WriteString("## Environment Context (环境与时空状态)\n")
	sb.WriteString(fmt.Sprintf("- Current Time: %s\n", time.Now().Format("2006-01-02 15:04:05 -0700 MST (Monday)")))
	sb.WriteString(fmt.Sprintf("- Host Platform: %s/%s\n", runtime.GOOS, runtime.GOARCH))
	if cleanDir != "" {
		sb.WriteString(fmt.Sprintf("- Working Directory: %s\n", cleanDir))
	}

	if gitInfo := detectGitBranch(cleanDir); gitInfo != "" {
		sb.WriteString(fmt.Sprintf("- Git Context: %s\n", gitInfo))
	}

	return strings.TrimSpace(sb.String())
}

func detectGitBranch(workDir string) string {
	headPath := filepath.Join(workDir, ".git", "HEAD")
	data, err := os.ReadFile(headPath)
	if err != nil {
		return ""
	}
	content := strings.TrimSpace(string(data))
	if strings.HasPrefix(content, "ref: refs/heads/") {
		branch := strings.TrimPrefix(content, "ref: refs/heads/")
		return fmt.Sprintf("branch %q", branch)
	}
	if len(content) >= 7 {
		return fmt.Sprintf("detached HEAD at %s", content[:7])
	}
	return ""
}

// composeSystemPrompt 将静态 basePersona、动态环境上下文与实时长期记忆合成为最终系统提示词。
func composeSystemPrompt(basePersona, workDir string) string {
	envBlock := composeEnvironmentContext(workDir)
	memoryBlock := memory.LoadBundle(workDir).FormatForPrompt()

	var sb strings.Builder
	sb.WriteString(basePersona)
	if envBlock != "" {
		sb.WriteString("\n\n" + envBlock)
	}
	if memoryBlock != "" {
		sb.WriteString("\n\n" + memoryBlock)
	}
	return sb.String()
}
