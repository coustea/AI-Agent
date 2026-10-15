package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"my-agent/internal/gateway"
	"my-agent/internal/memory"
	"my-agent/internal/tool"
)

// mockGateway 用于测试 Agent 多轮对话与流式输出的测试桩
type mockGateway struct {
	mu       sync.Mutex
	requests []*gateway.ChatRequest
	replies  []string
	callIdx  int
}

func newMockGateway(replies ...string) *mockGateway {
	return &mockGateway{
		replies: replies,
	}
}

func (m *mockGateway) Chat(ctx context.Context, req *gateway.ChatRequest) (*gateway.ChatResponse, error) {
	return nil, nil
}

func (m *mockGateway) ChatStream(ctx context.Context, req *gateway.ChatRequest) (<-chan gateway.StreamChunk, error) {
	m.mu.Lock()
	m.requests = append(m.requests, req)
	idx := m.callIdx
	m.callIdx++
	m.mu.Unlock()

	reply := "Default reply"
	if idx < len(m.replies) {
		reply = m.replies[idx]
	}

	ch := make(chan gateway.StreamChunk, 8)
	go func() {
		defer close(ch)

		// 模拟流式切词分片下发
		parts := strings.Split(reply, " ")
		for i, part := range parts {
			delta := part
			if i < len(parts)-1 {
				delta += " "
			}
			ch <- gateway.StreamChunk{Delta: delta}
		}

		ch <- gateway.StreamChunk{
			Done: true,
			Usage: &gateway.Usage{
				PromptTokens:     10,
				CompletionTokens: 5,
				TotalTokens:      15,
			},
		}
	}()

	return ch, nil
}

func (m *mockGateway) TotalUsage() gateway.Usage {
	return gateway.Usage{TotalTokens: 15}
}

// 测试多轮对话上下文累加与记忆保留
func TestCoreAgent_MultiTurn_Memory(t *testing.T) {
	mockGW := newMockGateway(
		"Hello! Nice to meet you, Coustea.",
		"Your name is Coustea, as you mentioned earlier.",
	)

	ag, err := NewAgent(mockGW, WithSystemPrompt("Test System Prompt"))
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	// ========== 第一轮对话 ==========
	stream1, err := ag.StreamRun(ctx, "Hello, my name is Coustea.")
	if err != nil {
		t.Fatalf("turn 1 StreamRun failed: %v", err)
	}

	var text1 strings.Builder
	var done1 bool
	var usage1 *gateway.Usage

	for ev := range stream1 {
		if ev.Err != nil {
			t.Fatalf("turn 1 unexpected error: %v", ev.Err)
		}
		if ev.Delta != "" {
			text1.WriteString(ev.Delta)
		}
		if ev.Done {
			done1 = true
			usage1 = ev.Usage
		}
	}

	if !done1 {
		t.Errorf("turn 1 expected Done=true")
	}
	if text1.String() != "Hello! Nice to meet you, Coustea." {
		t.Errorf("turn 1 unexpected reply: %q", text1.String())
	}
	if usage1 == nil || usage1.TotalTokens != 15 {
		t.Errorf("turn 1 unexpected usage: %+v", usage1)
	}

	// 验证第一轮后历史记忆包含 2 条消息
	history1 := ag.History()
	if len(history1) != 2 {
		t.Fatalf("expected 2 history messages after turn 1, got %d", len(history1))
	}
	if history1[0].Role != gateway.RoleUser || history1[0].Content != "Hello, my name is Coustea." {
		t.Errorf("unexpected history[0]: %+v", history1[0])
	}
	if history1[1].Role != gateway.RoleAssistant || history1[1].Content != "Hello! Nice to meet you, Coustea." {
		t.Errorf("unexpected history[1]: %+v", history1[1])
	}

	// ========== 第二轮对话 ==========
	stream2, err := ag.StreamRun(ctx, "What is my name?")
	if err != nil {
		t.Fatalf("turn 2 StreamRun failed: %v", err)
	}

	var text2 strings.Builder
	for ev := range stream2 {
		if ev.Delta != "" {
			text2.WriteString(ev.Delta)
		}
	}

	if text2.String() != "Your name is Coustea, as you mentioned earlier." {
		t.Errorf("turn 2 unexpected reply: %q", text2.String())
	}

	// 关键验证：检查发给网关的请求中，是否携带了完整的历史上下文！
	mockGW.mu.Lock()
	if len(mockGW.requests) != 2 {
		t.Fatalf("expected 2 gateway requests, got %d", len(mockGW.requests))
	}
	req2 := mockGW.requests[1]
	mockGW.mu.Unlock()

	// req2 应该包含：System, User1, Assistant1, User2 (共 4 条)
	if len(req2.Messages) != 4 {
		t.Fatalf("turn 2 request expected 4 messages, got %d", len(req2.Messages))
	}
	if req2.Messages[0].Role != gateway.RoleSystem {
		t.Errorf("expected System prompt first, got: %+v", req2.Messages[0])
	}
	if req2.Messages[1].Content != "Hello, my name is Coustea." {
		t.Errorf("expected User1 in context, got: %+v", req2.Messages[1])
	}
	if req2.Messages[2].Content != "Hello! Nice to meet you, Coustea." {
		t.Errorf("expected Assistant1 in context, got: %+v", req2.Messages[2])
	}
	if req2.Messages[3].Content != "What is my name?" {
		t.Errorf("expected User2 in context, got: %+v", req2.Messages[3])
	}

	// 验证第二轮后总历史共有 4 条消息
	history2 := ag.History()
	if len(history2) != 4 {
		t.Fatalf("expected 4 history messages after turn 2, got %d", len(history2))
	}
}

// 测试 Reset 清空会话
func TestCoreAgent_Reset(t *testing.T) {
	mockGW := newMockGateway("Hi")
	ag, _ := NewAgent(mockGW)

	stream, _ := ag.StreamRun(context.Background(), "Msg")
	for range stream {
	}
	if len(ag.History()) == 0 {
		t.Fatalf("expected history to have messages")
	}

	ag.Reset()
	if len(ag.History()) != 0 {
		t.Errorf("expected empty history after reset, got %d", len(ag.History()))
	}
}

// 测试 SetGateway 无损热切换底层模型并保留当前记忆
func TestCoreAgent_SetGateway(t *testing.T) {
	mockGW1 := newMockGateway("Reply 1")
	ag, _ := NewAgent(mockGW1)

	stream1, _ := ag.StreamRun(context.Background(), "Question 1")
	for range stream1 {
	}
	if len(ag.History()) != 2 {
		t.Fatalf("expected 2 messages in history, got %d", len(ag.History()))
	}

	// 热切换为网关 2
	mockGW2 := newMockGateway("Reply 2 from new model")
	ag.SetGateway(mockGW2)

	// 记忆未丢失
	if len(ag.History()) != 2 {
		t.Errorf("expected history to be preserved after SetGateway, got %d", len(ag.History()))
	}

	// 运行新对话由新网关承接
	stream, err := ag.StreamRun(context.Background(), "Question 2")
	if err != nil {
		t.Fatalf("StreamRun failed after SetGateway: %v", err)
	}

	var text strings.Builder
	for ev := range stream {
		if ev.Delta != "" {
			text.WriteString(ev.Delta)
		}
	}

	if text.String() != "Reply 2 from new model" {
		t.Errorf("expected response from new gateway, got %q", text.String())
	}
}

// 测试防止并发重复进入的防重锁
func TestCoreAgent_ConcurrentRun_Lock(t *testing.T) {
	blockCh := make(chan struct{})
	mockGW := &mockGateway{}
	// 自定义一个阻塞式的 ChatStream
	ag, _ := NewAgent(mockGW)
	ag.gw = &blockingGateway{blockCh: blockCh}

	ctx := context.Background()

	// 启动第一个轮次
	stream1, err := ag.StreamRun(ctx, "Turn 1")
	if err != nil {
		t.Fatalf("first run failed: %v", err)
	}

	// 立即尝试启动第二个轮次，应该被拒绝
	_, err2 := ag.StreamRun(ctx, "Turn 2")
	if err2 != ErrRunInProgress {
		t.Errorf("expected ErrRunInProgress, got: %v", err2)
	}

	// 释放第一个轮次
	close(blockCh)
	for range stream1 {
	}

	// 第一个轮次结束后，再次启动应该成功
	stream3, err3 := ag.StreamRun(ctx, "Turn 3")
	if err3 != nil {
		t.Errorf("expected run to succeed after completion, got: %v", err3)
	}
	for range stream3 {
	}
}

type blockingGateway struct {
	blockCh <-chan struct{}
}

func (b *blockingGateway) Chat(ctx context.Context, req *gateway.ChatRequest) (*gateway.ChatResponse, error) {
	return nil, nil
}

func (b *blockingGateway) ChatStream(ctx context.Context, req *gateway.ChatRequest) (<-chan gateway.StreamChunk, error) {
	ch := make(chan gateway.StreamChunk, 2)
	go func() {
		defer close(ch)
		<-b.blockCh
		ch <- gateway.StreamChunk{Delta: "Done", Done: true}
	}()
	return ch, nil
}

func (b *blockingGateway) TotalUsage() gateway.Usage {
	return gateway.Usage{}
}

// 测试边界校验与空参数
func TestCoreAgent_Validation(t *testing.T) {
	_, err := NewAgent(nil)
	if !errors.Is(err, ErrNilGateway) {
		t.Errorf("expected ErrNilGateway, got: %v", err)
	}

	ag, _ := NewAgent(&mockGateway{}, WithMemory(memory.NewSlidingWindowMemory(10)), WithMaxSteps(5))
	_, err = ag.StreamRun(context.Background(), "   ")
	if !errors.Is(err, ErrEmptyPrompt) {
		t.Errorf("expected ErrEmptyPrompt, got: %v", err)
	}
}

type toolCallStepGateway struct {
	mu    sync.Mutex
	steps []func(req *gateway.ChatRequest) []gateway.StreamChunk
	calls int
}

func (m *toolCallStepGateway) Chat(ctx context.Context, req *gateway.ChatRequest) (*gateway.ChatResponse, error) {
	return nil, nil
}

func (m *toolCallStepGateway) ChatStream(ctx context.Context, req *gateway.ChatRequest) (<-chan gateway.StreamChunk, error) {
	m.mu.Lock()
	idx := m.calls
	m.calls++
	m.mu.Unlock()

	ch := make(chan gateway.StreamChunk, 4)
	go func() {
		defer close(ch)
		if idx < len(m.steps) {
			chunks := m.steps[idx](req)
			for _, c := range chunks {
				ch <- c
			}
		}
	}()
	return ch, nil
}

func (m *toolCallStepGateway) TotalUsage() gateway.Usage {
	return gateway.Usage{}
}

type mockAdderTool struct{}

func (m *mockAdderTool) Name() string        { return "adder" }
func (m *mockAdderTool) Description() string { return "Add two numbers" }
func (m *mockAdderTool) Schema() json.RawMessage {
	return json.RawMessage(`{
		"type": "object",
		"properties": {
			"a": {"type": "number"},
			"b": {"type": "number"}
		},
		"required": ["a", "b"]
	}`)
}
func (m *mockAdderTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	var input struct {
		A float64 `json:"a"`
		B float64 `json:"b"`
	}
	if err := json.Unmarshal(args, &input); err != nil {
		return "", err
	}
	if input.A < 0 {
		return "", errors.New("negative numbers not supported")
	}
	return "result: " + strings.TrimRight(strings.TrimRight(string(json.RawMessage([]byte(string(rune(int(input.A+input.B)+'0'))))), "0"), "."), nil
}

// 测试 ReAct 循环：工具调用 -> 结果回传 -> 模型生成最终答复
func TestCoreAgent_ReAct_ToolExecution(t *testing.T) {
	reg := tool.NewRegistry(&mockAdderTool{})

	gw := &toolCallStepGateway{
		steps: []func(req *gateway.ChatRequest) []gateway.StreamChunk{
			// Step 1: 模型返回工具调用
			func(req *gateway.ChatRequest) []gateway.StreamChunk {
				if len(req.Tools) != 1 || req.Tools[0].Name != "adder" {
					t.Errorf("expected 1 tool 'adder' in request, got %v", req.Tools)
				}
				return []gateway.StreamChunk{
					{
						ToolCalls: []gateway.ToolCall{
							{
								ID:        "call_123",
								Name:      "adder",
								Arguments: json.RawMessage(`{"a": 2, "b": 3}`),
							},
						},
						Done: true,
					},
				}
			},
			// Step 2: 模型收到工具结果后生成最终文本答复
			func(req *gateway.ChatRequest) []gateway.StreamChunk {
				// 验证上下文历史中已经包含了 RoleTool
				lastMsg := req.Messages[len(req.Messages)-1]
				if lastMsg.Role != gateway.RoleTool || lastMsg.ToolResult == nil || lastMsg.ToolResult.IsError {
					t.Errorf("expected successful RoleTool message, got: %+v", lastMsg)
				}
				return []gateway.StreamChunk{
					{Delta: "The sum is 5."},
					{Done: true},
				}
			},
		},
	}

	ag, err := NewAgent(gw, WithTools(reg))
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	stream, err := ag.StreamRun(context.Background(), "Please calculate 2 + 3")
	if err != nil {
		t.Fatalf("StreamRun failed: %v", err)
	}

	var events []AgentEvent
	for ev := range stream {
		events = append(events, ev)
	}

	// 验证关键事件流：ToolCallStart -> ToolCallResult -> TextDelta -> Done
	var hasToolStart, hasToolResult, hasDone bool
	var finalAnswer strings.Builder

	for _, ev := range events {
		switch ev.Type {
		case EventToolCallStart:
			hasToolStart = true
			if ev.ToolCall.Name != "adder" {
				t.Errorf("unexpected tool call: %v", ev.ToolCall)
			}
		case EventToolCallResult:
			hasToolResult = true
			if ev.ToolResult.IsError {
				t.Errorf("tool execution failed unexpectedly: %v", ev.ToolResult.Content)
			}
		case EventTextDelta:
			finalAnswer.WriteString(ev.Delta)
		case EventDone:
			hasDone = true
		}
	}

	if !hasToolStart || !hasToolResult || !hasDone {
		t.Errorf("missing events: hasToolStart=%v, hasToolResult=%v, hasDone=%v", hasToolStart, hasToolResult, hasDone)
	}
	if finalAnswer.String() != "The sum is 5." {
		t.Errorf("unexpected final text: %q", finalAnswer.String())
	}
}

// 测试 ReAct 循环错误自愈原则：工具报错包裹为 Observation 回传模型，不中断循环
func TestCoreAgent_ReAct_ErrorAsObservation(t *testing.T) {
	reg := tool.NewRegistry(&mockAdderTool{})

	gw := &toolCallStepGateway{
		steps: []func(req *gateway.ChatRequest) []gateway.StreamChunk{
			// Step 1: 模型传入非法负数参数触发工具报错
			func(req *gateway.ChatRequest) []gateway.StreamChunk {
				return []gateway.StreamChunk{
					{
						ToolCalls: []gateway.ToolCall{
							{
								ID:        "call_neg",
								Name:      "adder",
								Arguments: json.RawMessage(`{"a": -5, "b": 3}`),
							},
						},
						Done: true,
					},
				}
			},
			// Step 2: 模型收到错误 Observation，进行自愈回答
			func(req *gateway.ChatRequest) []gateway.StreamChunk {
				lastMsg := req.Messages[len(req.Messages)-1]
				if lastMsg.Role != gateway.RoleTool || lastMsg.ToolResult == nil || !lastMsg.ToolResult.IsError {
					t.Errorf("expected RoleTool with IsError=true, got: %+v", lastMsg)
				}
				return []gateway.StreamChunk{
					{Delta: "I cannot compute this because negative numbers are not supported."},
					{Done: true},
				}
			},
		},
	}

	ag, _ := NewAgent(gw, WithTools(reg))
	stream, err := ag.StreamRun(context.Background(), "Calculate -5 + 3")
	if err != nil {
		t.Fatalf("StreamRun failed: %v", err)
	}

	var errorObsSeen bool
	var finalAnswer strings.Builder
	for ev := range stream {
		if ev.Type == EventToolCallResult && ev.ToolResult.IsError {
			errorObsSeen = true
		}
		if ev.Type == EventTextDelta {
			finalAnswer.WriteString(ev.Delta)
		}
	}

	if !errorObsSeen {
		t.Errorf("expected error observation to be emitted")
	}
	if !strings.Contains(finalAnswer.String(), "negative numbers are not supported") {
		t.Errorf("expected model explanation, got: %q", finalAnswer.String())
	}
}

// 测试最大迭代轮次熔断
func TestCoreAgent_MaxStepsExceeded(t *testing.T) {
	reg := tool.NewRegistry(&mockAdderTool{})

	// 模拟无限调用工具的模型
	gw := &toolCallStepGateway{
		steps: []func(req *gateway.ChatRequest) []gateway.StreamChunk{
			func(req *gateway.ChatRequest) []gateway.StreamChunk {
				return []gateway.StreamChunk{
					{
						ToolCalls: []gateway.ToolCall{
							{ID: "c1", Name: "adder", Arguments: json.RawMessage(`{"a":1,"b":1}`)},
						},
						Done: true,
					},
				}
			},
			func(req *gateway.ChatRequest) []gateway.StreamChunk {
				return []gateway.StreamChunk{
					{
						ToolCalls: []gateway.ToolCall{
							{ID: "c2", Name: "adder", Arguments: json.RawMessage(`{"a":1,"b":1}`)},
						},
						Done: true,
					},
				}
			},
			func(req *gateway.ChatRequest) []gateway.StreamChunk {
				return []gateway.StreamChunk{
					{
						ToolCalls: []gateway.ToolCall{
							{ID: "c3", Name: "adder", Arguments: json.RawMessage(`{"a":1,"b":1}`)},
						},
						Done: true,
					},
				}
			},
		},
	}

	// 限制最多 2 步
	ag, _ := NewAgent(gw, WithTools(reg), WithMaxSteps(2))
	stream, err := ag.StreamRun(context.Background(), "Loop forever")
	if err != nil {
		t.Fatalf("StreamRun failed: %v", err)
	}

	var maxStepsErrSeen bool
	for ev := range stream {
		if ev.Type == EventError && errors.Is(ev.Err, ErrMaxSteps) {
			maxStepsErrSeen = true
		}
	}

	if !maxStepsErrSeen {
		t.Errorf("expected ErrMaxSteps error event")
	}
}

// 测试 coustea 个人智能体名称与工作目录自动注入系统提示词
func TestCoreAgent_WorkDir_And_SystemPrompt(t *testing.T) {
	gw := &mockGateway{}

	// 1. 默认构建：系统提示词自动注入当前工作目录并表明身份
	agDefault, err := NewAgent(gw)
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	prompt := agDefault.SystemPrompt()
	if !strings.Contains(prompt, "coustea") {
		t.Errorf("expected system prompt to contain 'coustea', got: %s", prompt)
	}
	if !strings.Contains(prompt, "general-purpose local AI personal assistant") {
		t.Errorf("expected system prompt to state general-purpose assistant, got: %s", prompt)
	}
	if !strings.Contains(prompt, "Long-Term Memory") {
		t.Errorf("expected system prompt to contain Long-Term Memory section, got: %s", prompt)
	}

	currentWd, _ := os.Getwd()
	if !strings.Contains(prompt, currentWd) {
		t.Errorf("expected system prompt to contain current workdir %q, got: %s", currentWd, prompt)
	}

	// 2. 指定 WithWorkDir：工作目录与系统提示词同步更新
	customDir := "/Users/test/my-workspace"
	agCustomDir, err := NewAgent(gw, WithWorkDir(customDir))
	if err != nil {
		t.Fatalf("failed to create agent with custom workdir: %v", err)
	}

	if agCustomDir.WorkDir() != customDir {
		t.Errorf("expected workdir %s, got %s", customDir, agCustomDir.WorkDir())
	}
	if !strings.Contains(agCustomDir.SystemPrompt(), customDir) {
		t.Errorf("expected custom system prompt to contain %s, got: %s", customDir, agCustomDir.SystemPrompt())
	}

	// 3. 显式覆盖 WithSystemPrompt
	agCustomPrompt, err := NewAgent(gw, WithSystemPrompt("Explicit custom prompt"))
	if err != nil {
		t.Fatalf("failed to create agent with custom prompt: %v", err)
	}
	if agCustomPrompt.SystemPrompt() != "Explicit custom prompt" {
		t.Errorf("expected explicit prompt, got: %s", agCustomPrompt.SystemPrompt())
	}
}

// 测试整个系统通过 Agent 经过 Gateway 网关分配并正常调用具体模型的完整端到端链路
func TestAgent_EndToEnd_ModelExecution(t *testing.T) {
	// 1. 模拟 Google Gemini 官方端点
	geminiServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("x-goog-api-key") != "gemini-secret" {
			http.Error(w, "invalid google key", http.StatusUnauthorized)
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		flusher := w.(http.Flusher)
		_, _ = fmt.Fprintf(w, "data: {\"choices\":[{\"delta\":{\"content\":\"Hello from Gemini\"}}]}\n\n")
		flusher.Flush()
		_, _ = fmt.Fprintf(w, "data: [DONE]\n\n")
		flusher.Flush()
	}))
	defer geminiServer.Close()

	// 2. 模拟 DeepSeek 端点 (支持深度思考链)
	dsServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer ds-secret" {
			http.Error(w, "invalid ds key", http.StatusUnauthorized)
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		flusher := w.(http.Flusher)
		_, _ = fmt.Fprintf(w, "data: {\"choices\":[{\"delta\":{\"reasoning_content\":\"DeepSeek thinking...\"}}]}\n\n")
		flusher.Flush()
		_, _ = fmt.Fprintf(w, "data: {\"choices\":[{\"delta\":{\"content\":\"Hello from DeepSeek\"}}]}\n\n")
		flusher.Flush()
		_, _ = fmt.Fprintf(w, "data: [DONE]\n\n")
		flusher.Flush()
	}))
	defer dsServer.Close()

	// 3. 构建独立提供商网关实例并装入网关路由器
	geminiGW, err := gateway.NewGemini(geminiServer.URL, "gemini-secret", "gemini-2.5-flash", geminiServer.Client())
	if err != nil {
		t.Fatalf("failed to create gemini gateway: %v", err)
	}
	dsGW, err := gateway.NewDeepSeek(dsServer.URL, "ds-secret", "deepseek-flash", dsServer.Client())
	if err != nil {
		t.Fatalf("failed to create deepseek gateway: %v", err)
	}

	router := gateway.NewRouter("gemini")
	router.Register("gemini", geminiGW)
	router.Register("deepseek", dsGW)

	// 4. 将网关注入 Agent 内核并挂载工具
	ag, err := NewAgent(router, WithDefaultTools())
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	// 场景 A: 默认路由到 Gemini 模型调用
	streamA, err := ag.StreamRun(context.Background(), "Hello")
	if err != nil {
		t.Fatalf("StreamRun to Gemini failed: %v", err)
	}
	var replyA strings.Builder
	for ev := range streamA {
		if ev.Delta != "" {
			replyA.WriteString(ev.Delta)
		}
	}
	if replyA.String() != "Hello from Gemini" {
		t.Errorf("expected 'Hello from Gemini', got %q", replyA.String())
	}

	// 场景 B: 运行时切换网关默认分配为 DeepSeek，验证深度思考与回答
	router.SetActive("deepseek")
	streamB, err := ag.StreamRun(context.Background(), "Think carefully")
	if err != nil {
		t.Fatalf("StreamRun to DeepSeek failed: %v", err)
	}
	var replyB strings.Builder
	for ev := range streamB {
		if ev.Delta != "" {
			replyB.WriteString(ev.Delta)
		}
	}
	if replyB.String() != "Hello from DeepSeek" {
		t.Errorf("expected 'Hello from DeepSeek', got %q", replyB.String())
	}
}
