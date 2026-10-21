package middleware

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"my-agent/internal/protocol"
	"my-agent/pkg/llm"
)

// LoggingMiddleware 是基于 Hook 思想实现的透明可观测性日志中间件。
// 它通过监听 Agent 生命周期的全量 Trace 数据，将每一轮对话中的：
// 1. 用户输入 (User Prompt)
// 2. 发送给大模型的完整上下文与可用工具参数 Schema (ChatRequest)
// 3. 大模型返回的原始思考链 (ReasoningContent) 与回复 (Content)
// 4. 工具调用的精确参数与执行结果 (ToolCall & ToolResult)
// 5. Token 消耗统计与总耗时 (Usage & Summary)
// 实时结构化收集为 []protocol.TraceEvent，并以 100% 原始 JSON 写入 .tide/logs/latest.json 与追加归档到 .tide/logs/agent.jsonl。
type LoggingMiddleware struct {
	mu         sync.RWMutex
	logDir     string
	latestJSON string
	jsonlFile  string
	events     []protocol.TraceEvent
}

// NewLoggingMiddleware 构造日志中间件实例
func NewLoggingMiddleware(workDir string) *LoggingMiddleware {
	if strings.TrimSpace(workDir) == "" {
		workDir = "."
	}
	dir := filepath.Join(workDir, ".tide", "logs")
	return &LoggingMiddleware{
		logDir:     dir,
		latestJSON: filepath.Join(dir, "latest.json"),
		jsonlFile:  filepath.Join(dir, "agent.jsonl"),
		events:     make([]protocol.TraceEvent, 0),
	}
}

// Traces 返回当前轮次已收集到的全部全量结构化追踪事件切片副本
func (l *LoggingMiddleware) Traces() []protocol.TraceEvent {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return append([]protocol.TraceEvent(nil), l.events...)
}

func (l *LoggingMiddleware) ensureDirLocked() {
	_ = os.MkdirAll(l.logDir, 0o755)
}

func (l *LoggingMiddleware) writeLatestJSONLocked() {
	l.ensureDirLocked()
	data, err := json.MarshalIndent(l.events, "", "  ")
	if err == nil {
		_ = os.WriteFile(l.latestJSON, data, 0o600)
	}
}

func (l *LoggingMiddleware) appendJSONLLocked(ev protocol.TraceEvent) {
	l.ensureDirLocked()
	f, err := os.OpenFile(l.jsonlFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err == nil {
		defer func() { _ = f.Close() }()
		line, err := json.Marshal(ev)
		if err == nil {
			_, _ = f.WriteString(string(line) + "\n")
		}
	}
}

// recordEvent 内存追加 + JSONL 追加（O(1) 逐事件审计通道）。
// latest.json 不在事件路径上重写——轮末统一快照，避免流式回调路径上的写放大。
func (l *LoggingMiddleware) recordEvent(ev protocol.TraceEvent) {
	l.mu.Lock()
	defer l.mu.Unlock()

	l.events = append(l.events, ev)
	l.appendJSONLLocked(ev)
}

// OnTurnStart 单轮交互开始
func (l *LoggingMiddleware) OnTurnStart(ctx context.Context, turnID, prompt string) {
	l.mu.Lock()
	l.events = make([]protocol.TraceEvent, 0)
	l.mu.Unlock()

	l.recordEvent(protocol.TraceEvent{
		Step:      -1,
		Type:      "turn_start",
		Title:     "👤 用户提问 · 新轮次开启",
		Timestamp: time.Now(),
		Payload: map[string]any{
			"turn_id":   turnID,
			"prompt":    prompt,
			"timestamp": time.Now().Format(time.RFC3339),
		},
	})
}

// OnLLMRequest 每步发起大模型调用前
func (l *LoggingMiddleware) OnLLMRequest(ctx context.Context, req *protocol.LLMRequestTrace) {
	l.recordEvent(protocol.TraceEvent{
		Step:      req.Step,
		Type:      "llm_req",
		Title:     fmt.Sprintf("Step %d · 📤 LLM 请求上下文 (%s)", req.Step, req.ModelName),
		Timestamp: req.Timestamp,
		Payload: map[string]any{
			"step":          req.Step,
			"base_url":      req.BaseURL,
			"model":         req.ModelName,
			"system_prompt": req.SystemPrompt,
			"messages":      req.Messages,
			"tools":         req.Tools,
		},
	})
}

// OnLLMResponse 大模型决策返回完毕后
func (l *LoggingMiddleware) OnLLMResponse(ctx context.Context, resp *protocol.LLMResponseTrace) {
	var errStr string
	if resp.Error != nil {
		errStr = resp.Error.Error()
	}

	respPayload := map[string]any{
		"step":              resp.Step,
		"duration_ms":       resp.Duration.Milliseconds(),
		"reply":             resp.Reply,
		"reasoning_content": resp.ReasoningContent,
		"tool_calls":        resp.ToolCalls,
		"usage":             resp.Usage,
		"error":             errStr,
	}

	if len(resp.ToolCalls) > 0 {
		var callsSummary []map[string]any
		for _, tc := range resp.ToolCalls {
			var parsedArgs any
			if err := json.Unmarshal([]byte(tc.Arguments), &parsedArgs); err != nil {
				parsedArgs = tc.Arguments
			}
			callsSummary = append(callsSummary, map[string]any{
				"id":        tc.ID,
				"name":      tc.Name,
				"arguments": parsedArgs,
			})
		}
		respPayload["tool_calls"] = callsSummary
	}

	title := fmt.Sprintf("Step %d · 📥 LLM 决策回复", resp.Step)
	if resp.ReasoningContent != "" && len(resp.ToolCalls) > 0 {
		title = fmt.Sprintf("Step %d · 💭 思考链推演并调用 %d 个工具", resp.Step, len(resp.ToolCalls))
	} else if len(resp.ToolCalls) > 0 {
		title = fmt.Sprintf("Step %d · ⚡ 发起 %d 个工具调用", resp.Step, len(resp.ToolCalls))
	} else if resp.Reply != "" {
		title = fmt.Sprintf("Step %d · 💬 大模型生成最终回答", resp.Step)
	}

	l.recordEvent(protocol.TraceEvent{
		Step:      resp.Step,
		Type:      "llm_resp",
		Title:     title,
		Timestamp: time.Now(),
		Duration:  resp.Duration,
		Payload:   respPayload,
	})
}

// OnToolStart 工具调用开始前
func (l *LoggingMiddleware) OnToolStart(ctx context.Context, step int, call llm.ToolCall) {
	var parsedArgs any
	if err := json.Unmarshal([]byte(call.Arguments), &parsedArgs); err != nil {
		parsedArgs = call.Arguments
	}

	l.recordEvent(protocol.TraceEvent{
		Step:      step,
		Type:      "tool_start",
		Title:     fmt.Sprintf("Step %d · ⚙️ 开始调用工具: %s", step, call.Name),
		Timestamp: time.Now(),
		Payload: map[string]any{
			"step":         step,
			"tool_call_id": call.ID,
			"tool_name":    call.Name,
			"arguments":    parsedArgs,
		},
	})
}

// OnToolEnd 工具调用执行完毕后
func (l *LoggingMiddleware) OnToolEnd(ctx context.Context, trace *protocol.ToolTrace) {
	var parsedArgs any
	if err := json.Unmarshal([]byte(trace.Call.Arguments), &parsedArgs); err != nil {
		parsedArgs = trace.Call.Arguments
	}

	statusText := "✔ 成功"
	if trace.Result.IsError {
		statusText = "❌ 异常"
	}

	l.recordEvent(protocol.TraceEvent{
		Step:      trace.Step,
		Type:      "tool_end",
		Title:     fmt.Sprintf("Step %d · 🔧 工具执行结果: %s (%s)", trace.Step, trace.Call.Name, statusText),
		Timestamp: trace.Timestamp,
		Duration:  trace.Duration,
		Payload: map[string]any{
			"step":         trace.Step,
			"tool_call_id": trace.Call.ID,
			"tool_name":    trace.Call.Name,
			"arguments":    parsedArgs,
			"duration_ms":  trace.Duration.Milliseconds(),
			"is_error":     trace.Result.IsError,
			"output":       trace.Result.Content,
		},
	})
}

// OnTurnEnd 单轮交互完整收敛结束
func (l *LoggingMiddleware) OnTurnEnd(ctx context.Context, summary *protocol.TurnSummaryTrace) {
	status := "completed"
	if !summary.Success {
		status = "failed"
	}
	var errStr string
	if summary.Error != nil {
		errStr = summary.Error.Error()
	}

	l.recordEvent(protocol.TraceEvent{
		Step:      -1,
		Type:      "turn_end",
		Title:     fmt.Sprintf("🏁 轮次收敛总结 (%d 步, %d tokens, %v)", summary.TotalSteps, summary.TotalUsage.TotalTokens, summary.Duration.Round(time.Millisecond)),
		Timestamp: time.Now(),
		Duration:  summary.Duration,
		Payload: map[string]any{
			"turn_id":     summary.TurnID,
			"prompt":      summary.Prompt,
			"total_steps": summary.TotalSteps,
			"total_usage": summary.TotalUsage,
			"duration_ms": summary.Duration.Milliseconds(),
			"status":      status,
			"error":       errStr,
		},
	})

	// 轮末快照：一次性写入本轮全量事件（轮内数据已由 agent.jsonl 保证完整）
	l.mu.Lock()
	l.writeLatestJSONLocked()
	l.mu.Unlock()
}
