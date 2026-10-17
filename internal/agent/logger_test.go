package agent

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"my-agent/internal/protocol"
	"my-agent/internal/tool"
)

// TestLoggingMiddleware_FullLifecycle 验证完整 ReAct 循环（思考链、工具调用、回复、用量汇总）被透明记录并落盘
func TestLoggingMiddleware_FullLifecycle(t *testing.T) {
	tmpDir := t.TempDir()

	// 注册一个测试工具
	reg := tool.NewRegistry(&simpleTestTool{
		name: "read_file",
		fn: func(ctx context.Context, args json.RawMessage) (string, error) {
			return "host: 127.0.0.1\nport: 8080", nil
		},
	})

	// 模拟两步 ReAct 网关：
	// Step 0: 思考并请求调用 read_file 工具
	// Step 1: 思考并给出最终文本回复
	gw := &toolCallStepGateway{
		steps: []func(req *protocol.ChatRequest) []protocol.ChatResponse{
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{ReasoningContent: "I need to read the config file first.\nThen I can answer the user."},
					{
						ToolCalls: []protocol.ToolCall{
							{ID: "call_test_1", Name: "read_file", Arguments: `{"path": "config.yaml"}`},
						},
						Usage: &protocol.Usage{PromptTokens: 100, CompletionTokens: 20, TotalTokens: 120},
						Done:  true,
					},
				}
			},
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{ReasoningContent: "I have received the config content.\nNow answering."},
					{Delta: "The host is 127.0.0.1 and port is 8080."},
					{
						Usage: &protocol.Usage{PromptTokens: 150, CompletionTokens: 30, TotalTokens: 180},
						Done:  true,
					},
				}
			},
		},
	}

	ag, err := NewAgent(gw,
		WithWorkDir(tmpDir),
		WithTools(reg),
		WithLoggingMiddleware(tmpDir),
	)
	if err != nil {
		t.Fatalf("NewAgent failed: %v", err)
	}

	stream, err := ag.StreamRun(context.Background(), "What is the host and port in config?")
	if err != nil {
		t.Fatalf("StreamRun failed: %v", err)
	}

	// 排空事件通道
	for ev := range stream {
		_ = ev
	}

	// 1. 验证 latest.md 内容排版与关键要素
	latestPath := filepath.Join(tmpDir, ".coustea", "logs", "latest.md")
	mdBytes, err := os.ReadFile(latestPath)
	if err != nil {
		t.Fatalf("failed to read latest.md: %v", err)
	}
	md := string(mdBytes)

	expectedSnippets := []string{
		"# 🚀 Coustea Agent Execution Trace",
		"What is the host and port in config?",
		"## 🔁 Step 0: LLM Reasoning & Decision",
		"### 2. LLM Raw Thinking Process (思考链)",
		"> I need to read the config file first.",
		"> Then I can answer the user.",
		"### 3. LLM Decision (Assistant Output)",
		"`read_file` (id: `call_test_1`) with arguments: `{\"path\": \"config.yaml\"}`",
		"### 4. Tool Execution: `read_file`",
		"- **Call ID**: `call_test_1`",
		"**Status**: `✔ Success`",
		"host: 127.0.0.1",
		"## 🔁 Step 1: LLM Reasoning & Decision",
		"The host is 127.0.0.1 and port is 8080.",
		"## 🏁 Turn Summary",
		"- **Total Steps**: 2 steps",
		"- **Total Tokens**: 300 (Prompt: 250, Completion: 50)",
		"- **Status**: `✔ Completed Successfully`",
	}

	for _, snippet := range expectedSnippets {
		if !strings.Contains(md, snippet) {
			t.Errorf("expected latest.md to contain snippet:\n%s\n\nFull latest.md:\n%s", snippet, md)
		}
	}

	// 2. 验证 agent.log 追加流
	logPath := filepath.Join(tmpDir, ".coustea", "logs", "agent.log")
	logBytes, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatalf("failed to read agent.log: %v", err)
	}
	logStr := string(logBytes)

	logSnippets := []string{
		"[TURN START]",
		"prompt=\"What is the host and port in config?\"",
		"[LLM REQ] step=0",
		"[LLM RESP] step=0",
		"tool_calls=1",
		"[TOOL START] step=0 name=read_file id=call_test_1",
		"[TOOL END] step=0 name=read_file id=call_test_1",
		"[LLM REQ] step=1",
		"[LLM RESP] step=1",
		"[TURN END]",
		"steps=2 tokens=300",
		"success=true",
	}

	for _, s := range logSnippets {
		if !strings.Contains(logStr, s) {
			t.Errorf("expected agent.log to contain snippet %q, got:\n%s", s, logStr)
		}
	}
}

// TestLoggingMiddleware_MultipleTurns_LatestOverwritten_LogAppended 验证 latest.md 每轮覆盖，而 agent.log 持续追加
func TestLoggingMiddleware_MultipleTurns_LatestOverwritten_LogAppended(t *testing.T) {
	tmpDir := t.TempDir()

	mockGW := newMockGateway("Reply 1", "Reply 2")
	ag, err := NewAgent(mockGW,
		WithWorkDir(tmpDir),
		WithLoggingMiddleware(tmpDir),
	)
	if err != nil {
		t.Fatalf("NewAgent failed: %v", err)
	}

	// 第一轮对话
	stream1, _ := ag.StreamRun(context.Background(), "Question One")
	for range stream1 {
	}

	latestPath := filepath.Join(tmpDir, ".coustea", "logs", "latest.md")
	md1, _ := os.ReadFile(latestPath)
	if !strings.Contains(string(md1), "Question One") {
		t.Errorf("expected latest.md to contain Turn 1 question")
	}

	// 第二轮对话
	stream2, _ := ag.StreamRun(context.Background(), "Question Two")
	for range stream2 {
	}

	md2, _ := os.ReadFile(latestPath)
	md2Str := string(md2)
	if !strings.Contains(md2Str, "Question Two") {
		t.Errorf("expected latest.md to contain Turn 2 question")
	}
	if strings.Contains(md2Str, "Question One") {
		t.Errorf("expected latest.md to NOT contain Turn 1 question after being overwritten by Turn 2")
	}

	// 验证 agent.log 同时保留两轮对话
	logPath := filepath.Join(tmpDir, ".coustea", "logs", "agent.log")
	logBytes, _ := os.ReadFile(logPath)
	logStr := string(logBytes)
	if !strings.Contains(logStr, "Question One") || !strings.Contains(logStr, "Question Two") {
		t.Errorf("expected agent.log to append and retain both turns, got:\n%s", logStr)
	}
}

// TestLoggingMiddleware_ErrorTurn 验证错误或熔断轮次被清晰记录
func TestLoggingMiddleware_ErrorTurn(t *testing.T) {
	tmpDir := t.TempDir()

	// 模拟网关返回严重错误
	gwErr := &toolCallStepGateway{
		steps: []func(req *protocol.ChatRequest) []protocol.ChatResponse{
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{Err: errors.New("upstream service unavailable 503")},
				}
			},
		},
	}

	ag, _ := NewAgent(gwErr,
		WithWorkDir(tmpDir),
		WithLoggingMiddleware(tmpDir),
	)

	stream, _ := ag.StreamRun(context.Background(), "Will Fail")
	for range stream {
	}

	latestPath := filepath.Join(tmpDir, ".coustea", "logs", "latest.md")
	mdBytes, err := os.ReadFile(latestPath)
	if err != nil {
		t.Fatalf("failed to read latest.md: %v", err)
	}
	md := string(mdBytes)

	if !strings.Contains(md, "❌ Failed: upstream service unavailable 503") {
		t.Errorf("expected latest.md to record failure status, got:\n%s", md)
	}

	logPath := filepath.Join(tmpDir, ".coustea", "logs", "agent.log")
	logBytes, _ := os.ReadFile(logPath)
	logStr := string(logBytes)
	if !strings.Contains(logStr, "success=false") {
		t.Errorf("expected agent.log to record success=false, got:\n%s", logStr)
	}
}
