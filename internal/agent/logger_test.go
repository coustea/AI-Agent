package agent

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"my-agent/internal/middleware"
	"my-agent/internal/protocol"
	"my-agent/internal/tool"
	"my-agent/pkg/llm"
)

// TestLoggingMiddleware_FullLifecycle 验证完整 ReAct 循环被透明记录为 100% 原始 JSON 并落盘
func TestLoggingMiddleware_FullLifecycle(t *testing.T) {
	tmpDir := t.TempDir()

	// 注册一个测试工具
	reg := tool.NewRegistry(&simpleTestTool{
		name: "read_file",
		fn: func(ctx context.Context, args json.RawMessage) (string, error) {
			return "host: 127.0.0.1\nport: 8080", nil
		},
	})

	// 模拟两步 ReAct 大模型调用：
	// Step 0: 思考并请求调用 read_file 工具
	// Step 1: 思考并给出最终文本回复
	llmStub := &toolCallStepLLM{
		steps: []func(req llm.Request) []llm.Chunk{
			func(req llm.Request) []llm.Chunk {
				return []llm.Chunk{
					{ReasoningContent: "I need to read the config file first.\nThen I can answer the user."},
					{
						ToolCalls: []llm.ToolCall{
							{ID: "call_test_1", Name: "read_file", Arguments: `{"path": "config.yaml"}`},
						},
						Usage:  llm.Usage{PromptTokens: 100, CompletionTokens: 20, TotalTokens: 120},
						Finish: llm.StopEnd,
					},
				}
			},
			func(req llm.Request) []llm.Chunk {
				return []llm.Chunk{
					{ReasoningContent: "I have received the config content.\nNow answering."},
					{Delta: "The host is 127.0.0.1 and port is 8080."},
					{
						Usage:  llm.Usage{PromptTokens: 150, CompletionTokens: 30, TotalTokens: 180},
						Finish: llm.StopEnd,
					},
				}
			},
		},
	}

	lm := middleware.NewLoggingMiddleware(tmpDir)
	ag, err := NewAgent(llmStub,
		WithWorkDir(tmpDir),
		WithTools(reg),
		WithHook(lm),
	)
	if err != nil {
		t.Fatalf("NewAgent failed: %v", err)
	}

	stream, err := ag.Run(context.Background(), "What is the host and port in config?")
	if err != nil {
		t.Fatalf("Run failed: %v", err)
	}

	// 排空事件通道
	for range stream {
	}

	// 1. 验证日志中间件 Traces() 返回的内存数据完整性
	traces := lm.Traces()
	if len(traces) == 0 {
		t.Fatalf("expected non-empty traces from ag.Traces()")
	}

	// 验证包含必要事件类型
	eventTypes := make(map[string]bool)
	for _, ev := range traces {
		eventTypes[ev.Type] = true
		// 验证每个事件可被序列化
		if b, err := json.Marshal(ev); err != nil || len(b) == 0 {
			t.Errorf("event not serializable: %v (err=%v)", ev.Title, err)
		}
	}
	expectedTypes := []string{"turn_start", "llm_req", "llm_resp", "tool_start", "tool_end", "turn_end"}
	for _, et := range expectedTypes {
		if !eventTypes[et] {
			t.Errorf("missing expected event type %q in Traces()", et)
		}
	}

	// 2. 验证 latest.json 是合法、完整的 JSON 数组
	latestJSONPath := filepath.Join(tmpDir, ".tide", "logs", "latest.json")
	jsonBytes, err := os.ReadFile(latestJSONPath)
	if err != nil {
		t.Fatalf("failed to read latest.json: %v", err)
	}

	var loadedEvents []protocol.TraceEvent
	if err := json.Unmarshal(jsonBytes, &loadedEvents); err != nil {
		t.Fatalf("latest.json is not valid JSON array: %v", err)
	}
	if len(loadedEvents) != len(traces) {
		t.Errorf("expected %d events in latest.json, got %d", len(traces), len(loadedEvents))
	}

	// 3. 验证 agent.jsonl 逐行有效
	jsonlPath := filepath.Join(tmpDir, ".tide", "logs", "agent.jsonl")
	f, err := os.Open(jsonlPath)
	if err != nil {
		t.Fatalf("failed to read agent.jsonl: %v", err)
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	lineCount := 0
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var ev protocol.TraceEvent
		if err := json.Unmarshal([]byte(line), &ev); err != nil {
			t.Errorf("invalid json line in agent.jsonl: %v", err)
		}
		lineCount++
	}
	if lineCount == 0 {
		t.Errorf("expected lines in agent.jsonl, got 0")
	}
}

// TestLoggingMiddleware_MultipleTurns_LatestOverwritten_JSONLAppended 验证 latest.json 覆盖最新轮次，而 agent.jsonl 持续追加
func TestLoggingMiddleware_MultipleTurns_LatestOverwritten_JSONLAppended(t *testing.T) {
	tmpDir := t.TempDir()

	mockLLMClient := newMockLLM("Reply 1", "Reply 2")
	lm := middleware.NewLoggingMiddleware(tmpDir)
	ag, err := NewAgent(mockLLMClient,
		WithWorkDir(tmpDir),
		WithHook(lm),
	)
	if err != nil {
		t.Fatalf("NewAgent failed: %v", err)
	}

	// 第一轮对话
	stream1, _ := ag.Run(context.Background(), "Question One")
	for range stream1 {
	}

	latestPath := filepath.Join(tmpDir, ".tide", "logs", "latest.json")
	data1, _ := os.ReadFile(latestPath)
	if !strings.Contains(string(data1), "Question One") {
		t.Errorf("expected latest.json to contain Turn 1 question")
	}

	// 第二轮对话
	stream2, _ := ag.Run(context.Background(), "Question Two")
	for range stream2 {
	}

	data2, _ := os.ReadFile(latestPath)
	var eventsTurn2 []protocol.TraceEvent
	if err := json.Unmarshal(data2, &eventsTurn2); err != nil {
		t.Fatalf("failed to unmarshal latest.json after turn 2: %v", err)
	}

	if len(eventsTurn2) == 0 {
		t.Fatalf("latest.json empty after turn 2")
	}

	// 验证第一项和最后一项为 Turn 2
	startPayload := eventsTurn2[0].Payload.(map[string]any)
	if startPayload["prompt"] != "Question Two" {
		t.Errorf("expected latest.json turn_start prompt to be 'Question Two', got %v", startPayload["prompt"])
	}

	// 验证 agent.jsonl 同时保留两轮对话
	jsonlPath := filepath.Join(tmpDir, ".tide", "logs", "agent.jsonl")
	jsonlBytes, _ := os.ReadFile(jsonlPath)
	jsonlStr := string(jsonlBytes)
	if !strings.Contains(jsonlStr, "Question One") || !strings.Contains(jsonlStr, "Question Two") {
		t.Errorf("expected agent.jsonl to retain both turns, got:\n%s", jsonlStr)
	}
}

// TestLoggingMiddleware_ErrorTurn 验证错误或熔断轮次被清晰记录为结构化 JSON
func TestLoggingMiddleware_ErrorTurn(t *testing.T) {
	tmpDir := t.TempDir()

	llmErr := &toolCallStepLLM{
		steps: []func(req llm.Request) []llm.Chunk{
			func(req llm.Request) []llm.Chunk {
				return []llm.Chunk{
					{Err: errors.New("upstream service unavailable 503")},
				}
			},
		},
	}

	lm := middleware.NewLoggingMiddleware(tmpDir)
	ag, _ := NewAgent(llmErr,
		WithWorkDir(tmpDir),
		WithHook(lm),
	)

	stream, _ := ag.Run(context.Background(), "Will Fail")
	for range stream {
	}

	latestPath := filepath.Join(tmpDir, ".tide", "logs", "latest.json")
	data, err := os.ReadFile(latestPath)
	if err != nil {
		t.Fatalf("failed to read latest.json: %v", err)
	}
	str := string(data)
	if !strings.Contains(str, "upstream service unavailable 503") {
		t.Errorf("expected latest.json to record error, got:\n%s", str)
	}
}

// 验收 D6：latest.json 只在轮末快照写入，且落盘权限为 0600
func TestLoggingMiddleware_LatestJSONTurnEndOnly(t *testing.T) {
	dir := t.TempDir()
	lm := middleware.NewLoggingMiddleware(dir)
	latest := filepath.Join(dir, ".tide", "logs", "latest.json")
	jsonl := filepath.Join(dir, ".tide", "logs", "agent.jsonl")
	ctx := context.Background()

	lm.OnTurnStart(ctx, "turn_x", "hello")
	lm.OnLLMRequest(ctx, &protocol.LLMRequestTrace{Step: 0, Provider: "p", ModelName: "m", SystemPrompt: "sys"})

	if _, err := os.Stat(latest); !os.IsNotExist(err) {
		t.Fatalf("latest.json must NOT be written mid-turn (err=%v)", err)
	}
	if _, err := os.Stat(jsonl); err != nil {
		t.Fatalf("agent.jsonl must be appended per event: %v", err)
	}

	lm.OnTurnEnd(ctx, &protocol.TurnSummaryTrace{TurnID: "turn_x", Success: true})

	info, err := os.Stat(latest)
	if err != nil {
		t.Fatalf("latest.json must exist after turn end: %v", err)
	}
	if perm := info.Mode().Perm(); perm != 0o600 {
		t.Errorf("latest.json must be 0600, got %o", perm)
	}
	jinfo, err := os.Stat(jsonl)
	if err != nil {
		t.Fatalf("agent.jsonl stat failed: %v", err)
	}
	if perm := jinfo.Mode().Perm(); perm != 0o600 {
		t.Errorf("agent.jsonl must be 0600, got %o", perm)
	}

	data, err := os.ReadFile(latest)
	if err != nil {
		t.Fatal(err)
	}
	var evs []protocol.TraceEvent
	if err := json.Unmarshal(data, &evs); err != nil {
		t.Fatalf("latest.json must be valid JSON: %v", err)
	}
	if len(evs) != 3 {
		t.Errorf("expected full turn snapshot with 3 events, got %d", len(evs))
	}
}
