package agent

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"my-agent/internal/protocol"
)

// LoggingMiddleware 是基于 Hook 思想实现的透明可观测性日志中间件。
// 它通过监听 Agent 生命周期的全量 Trace 数据，将每一轮对话中的：
// 1. 用户输入
// 2. 发送给大模型的上下文与可用工具
// 3. 大模型返回的思考链 (ReasoningContent) 与回复 (Content)
// 4. 工具调用的参数与执行结果 (ToolCall & ToolResult)
// 5. Token 消耗统计与总耗时
// 实时结构化写入 .coustea/logs/latest.md（供开发者在 IDE 中实时查看）以及追加归档到 .coustea/logs/agent.log。
type LoggingMiddleware struct {
	mu       sync.Mutex
	logDir   string
	latestMD string
	logFile  string
	turnBuf  strings.Builder
}

// NewLoggingMiddleware 构造日志中间件实例
func NewLoggingMiddleware(workDir string) *LoggingMiddleware {
	if strings.TrimSpace(workDir) == "" {
		workDir = "."
	}
	dir := filepath.Join(workDir, ".coustea", "logs")
	return &LoggingMiddleware{
		logDir:   dir,
		latestMD: filepath.Join(dir, "latest.md"),
		logFile:  filepath.Join(dir, "agent.log"),
	}
}

func (l *LoggingMiddleware) ensureDirLocked() {
	_ = os.MkdirAll(l.logDir, 0o755)
}

func (l *LoggingMiddleware) writeLatestLocked() {
	l.ensureDirLocked()
	_ = os.WriteFile(l.latestMD, []byte(l.turnBuf.String()), 0o644)
}

func (l *LoggingMiddleware) appendLogLocked(line string) {
	l.ensureDirLocked()
	f, err := os.OpenFile(l.logFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err == nil {
		defer f.Close()
		_, _ = f.WriteString(line + "\n")
	}
}

// OnTurnStart 单轮交互开始
func (l *LoggingMiddleware) OnTurnStart(ctx context.Context, turnID string, prompt string) {
	l.mu.Lock()
	defer l.mu.Unlock()

	l.turnBuf.Reset()
	nowStr := time.Now().Format("2006-01-02 15:04:05")
	l.turnBuf.WriteString("# 🚀 Coustea Agent Execution Trace\n\n")
	l.turnBuf.WriteString(fmt.Sprintf("- **Turn ID**: `%s`\n", turnID))
	l.turnBuf.WriteString(fmt.Sprintf("- **Time**: `%s`\n", nowStr))
	l.turnBuf.WriteString(fmt.Sprintf("- **User Prompt**: `%s`\n\n", prompt))
	l.turnBuf.WriteString("---\n\n")
	l.writeLatestLocked()

	l.appendLogLocked(fmt.Sprintf("[%s] [TURN START] id=%s prompt=%q", nowStr, turnID, prompt))
}

// OnLLMRequest 每步发起大模型调用前
func (l *LoggingMiddleware) OnLLMRequest(ctx context.Context, req *LLMRequestTrace) {
	l.mu.Lock()
	defer l.mu.Unlock()

	l.turnBuf.WriteString(fmt.Sprintf("## 🔁 Step %d: LLM Reasoning & Decision\n\n", req.Step))
	l.turnBuf.WriteString("### 1. Request Context\n")
	if req.Provider != "" || req.ModelName != "" {
		l.turnBuf.WriteString(fmt.Sprintf("- **Provider / Model**: `%s` • `%s`\n", req.Provider, req.ModelName))
	}
	l.turnBuf.WriteString(fmt.Sprintf("- **Context Messages**: %d messages\n", len(req.Messages)))
	if len(req.Tools) > 0 {
		names := make([]string, 0, len(req.Tools))
		for _, t := range req.Tools {
			names = append(names, t.Name)
		}
		l.turnBuf.WriteString(fmt.Sprintf("- **Available Tools**: `[%s]`\n", strings.Join(names, ", ")))
	}
	l.turnBuf.WriteString("\n")
	l.writeLatestLocked()

	nowStr := time.Now().Format("2006-01-02 15:04:05")
	l.appendLogLocked(fmt.Sprintf("[%s] [LLM REQ] step=%d provider=%s model=%s messages=%d", nowStr, req.Step, req.Provider, req.ModelName, len(req.Messages)))
}

// OnLLMResponse 大模型决策返回完毕后
func (l *LoggingMiddleware) OnLLMResponse(ctx context.Context, resp *LLMResponseTrace) {
	l.mu.Lock()
	defer l.mu.Unlock()

	nowStr := time.Now().Format("2006-01-02 15:04:05")

	if resp.ReasoningContent != "" {
		l.turnBuf.WriteString("### 2. LLM Raw Thinking Process (思考链)\n")
		lines := strings.Split(strings.TrimSpace(resp.ReasoningContent), "\n")
		for _, line := range lines {
			l.turnBuf.WriteString("> " + line + "\n")
		}
		l.turnBuf.WriteString("\n")
	}

	if len(resp.ToolCalls) > 0 {
		l.turnBuf.WriteString("### 3. LLM Decision (Assistant Output)\n")
		if resp.Reply != "" {
			l.turnBuf.WriteString(fmt.Sprintf("- **Direct Reply**: %s\n", resp.Reply))
		} else {
			l.turnBuf.WriteString("- **Direct Reply**: *(none, decided to invoke tool)*\n")
		}
		l.turnBuf.WriteString("- **Tool Calls**:\n")
		for _, tc := range resp.ToolCalls {
			l.turnBuf.WriteString(fmt.Sprintf("  - `%s` (id: `%s`) with arguments: `%s`\n", tc.Name, tc.ID, tc.Arguments))
		}
		l.turnBuf.WriteString("\n")
	} else if resp.Reply != "" {
		l.turnBuf.WriteString("### 3. LLM Final Output\n\n")
		l.turnBuf.WriteString(resp.Reply + "\n\n")
	}

	if resp.Usage != nil && resp.Usage.TotalTokens > 0 {
		l.turnBuf.WriteString(fmt.Sprintf("- **Step Usage**: %d tokens (Prompt: %d, Completion: %d)\n\n",
			resp.Usage.TotalTokens, resp.Usage.PromptTokens, resp.Usage.CompletionTokens))
	}
	l.writeLatestLocked()

	toolCallsCount := len(resp.ToolCalls)
	totalTokens := 0
	if resp.Usage != nil {
		totalTokens = resp.Usage.TotalTokens
	}
	l.appendLogLocked(fmt.Sprintf("[%s] [LLM RESP] step=%d duration=%s tokens=%d tool_calls=%d",
		nowStr, resp.Step, resp.Duration.Round(time.Millisecond), totalTokens, toolCallsCount))
}

// OnToolStart 工具调用开始前
func (l *LoggingMiddleware) OnToolStart(ctx context.Context, step int, call protocol.ToolCall) {
	l.mu.Lock()
	defer l.mu.Unlock()

	nowStr := time.Now().Format("2006-01-02 15:04:05")
	l.appendLogLocked(fmt.Sprintf("[%s] [TOOL START] step=%d name=%s id=%s", nowStr, step, call.Name, call.ID))
}

// OnToolEnd 工具调用执行完毕后
func (l *LoggingMiddleware) OnToolEnd(ctx context.Context, trace *ToolTrace) {
	l.mu.Lock()
	defer l.mu.Unlock()

	l.turnBuf.WriteString(fmt.Sprintf("### 4. Tool Execution: `%s`\n\n", trace.Call.Name))
	l.turnBuf.WriteString(fmt.Sprintf("- **Call ID**: `%s`\n", trace.Call.ID))
	l.turnBuf.WriteString(fmt.Sprintf("- **Duration**: `%s` | ", trace.Duration.Round(time.Millisecond)))
	if trace.Result.IsError {
		l.turnBuf.WriteString("**Status**: `❌ Error`\n")
	} else {
		l.turnBuf.WriteString("**Status**: `✔ Success`\n")
	}
	l.turnBuf.WriteString("- **Output**:\n```\n" + trace.Result.Content + "\n```\n\n")
	l.writeLatestLocked()

	nowStr := time.Now().Format("2006-01-02 15:04:05")
	l.appendLogLocked(fmt.Sprintf("[%s] [TOOL END] step=%d name=%s id=%s duration=%s is_error=%v",
		nowStr, trace.Step, trace.Call.Name, trace.Call.ID, trace.Duration.Round(time.Millisecond), trace.Result.IsError))
}

// OnTurnEnd 单轮交互完整收敛结束
func (l *LoggingMiddleware) OnTurnEnd(ctx context.Context, summary *TurnSummaryTrace) {
	l.mu.Lock()
	defer l.mu.Unlock()

	l.turnBuf.WriteString("---\n\n")
	l.turnBuf.WriteString("## 🏁 Turn Summary\n\n")
	l.turnBuf.WriteString(fmt.Sprintf("- **Total Steps**: %d steps\n", summary.TotalSteps))
	l.turnBuf.WriteString(fmt.Sprintf("- **Total Tokens**: %d (Prompt: %d, Completion: %d)\n",
		summary.TotalUsage.TotalTokens, summary.TotalUsage.PromptTokens, summary.TotalUsage.CompletionTokens))
	l.turnBuf.WriteString(fmt.Sprintf("- **Total Duration**: %s\n", summary.Duration.Round(time.Millisecond)))
	if summary.Success {
		l.turnBuf.WriteString("- **Status**: `✔ Completed Successfully`\n\n")
	} else {
		errMsg := "Unknown"
		if summary.Error != nil {
			errMsg = summary.Error.Error()
		}
		l.turnBuf.WriteString(fmt.Sprintf("- **Status**: `❌ Failed: %s`\n\n", errMsg))
	}
	l.writeLatestLocked()

	nowStr := time.Now().Format("2006-01-02 15:04:05")
	l.appendLogLocked(fmt.Sprintf("[%s] [TURN END] id=%s steps=%d tokens=%d duration=%s success=%v",
		nowStr, summary.TurnID, summary.TotalSteps, summary.TotalUsage.TotalTokens, summary.Duration.Round(time.Millisecond), summary.Success))
}
