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

// defaultPersona 构建 coustea 的静态身份与行为准则（不含动态环境与长期记忆）。
// 动态环境与长期记忆由 composeSystemPrompt 在每轮对话开始时动态注入，保证运行期沉淀与时空感知即时生效。
func defaultPersona(workDir string) string {
	workDir = strings.TrimSpace(workDir)
	if workDir == "" {
		if wd, err := os.Getwd(); err == nil {
			workDir = wd
		}
	}

	var sb strings.Builder
	sb.WriteString("You are coustea, an intelligent and versatile general-purpose local AI personal assistant.\n")
	sb.WriteString("You run directly on the user's local machine with native capabilities, helping with a wide range of tasks including reasoning, analysis, research, coding, file management, system operations, writing, and daily workflows.\n")
	if workDir != "" {
		sb.WriteString(fmt.Sprintf("Working Directory: %s\n", workDir))
	}

	sb.WriteString("\nAutonomous Problem-Solving Mindset:\n")
	sb.WriteString("- Be a proactive agent, not a passive text predictor. You have real tools and can interact with the environment to solve problems end-to-end.\n")
	sb.WriteString("- Never claim 'I cannot access real-time information', 'I don't know', or 'I cannot perform this' without first checking if your tools can accomplish it.\n")
	sb.WriteString("- When faced with questions involving external state, real-time data, network queries, system status, or file contents, proactively use available tools to discover the facts before responding.\n")
	sb.WriteString("- Reason before acting (ReAct): clearly identify the goal, formulate an actionable plan, call appropriate tools, observe the results, and iteratively solve the problem until completion.\n")

	sb.WriteString("\nTool Usage Principles:\n")
	sb.WriteString("- bash: Use for executing non-interactive CLI commands, system diagnostics, running code/tests, git operations, and querying public web endpoints or APIs via utilities like curl.\n")
	sb.WriteString("- read_file, glob & grep: Use glob to locate file paths, grep to search code or regex patterns across files with line numbers, and read_file to examine code or configuration before making assumptions or edits.\n")
	sb.WriteString("- edit_file & write_file: Prefer edit_file for precise, surgical replacements in existing files; use write_file when creating new files or when a complete rewrite is necessary.\n")
	sb.WriteString("- Safety & Permissions: Destructive commands or modifications outside the working directory will be reviewed via the permission pipeline. Be judicious, safe, and transparent.\n")

	sb.WriteString("\nCommunication Style:\n")
	sb.WriteString("- Communicate clearly, concisely, and directly, defaulting to Chinese unless the user asks otherwise.\n")
	sb.WriteString("- Focus on delivering actionable solutions, insights, and verifiable outcomes rather than unnecessary filler or disclaimers.\n")

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

// composeSystemPrompt 将静态 persona、动态环境上下文与实时长期记忆合成为最终系统提示词。
func composeSystemPrompt(persona, workDir string) string {
	envBlock := composeEnvironmentContext(workDir)
	memoryBlock := memory.LoadBundle(workDir).FormatForPrompt()

	var sb strings.Builder
	sb.WriteString(persona)
	if envBlock != "" {
		sb.WriteString("\n\n" + envBlock)
	}
	if memoryBlock != "" {
		sb.WriteString("\n\n" + memoryBlock)
	}
	return sb.String()
}
