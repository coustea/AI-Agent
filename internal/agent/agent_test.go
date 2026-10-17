package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"my-agent/internal/config"
	"my-agent/internal/gateway"
	"my-agent/internal/memory"
	"my-agent/internal/protocol"
	"my-agent/internal/tool"
)

// mockGateway 用于测试 Agent 多轮对话与流式输出的测试桩
type mockGateway struct {
	mu       sync.Mutex
	requests []*protocol.ChatRequest
	replies  []string
	callIdx  int
}

func newMockGateway(replies ...string) *mockGateway {
	return &mockGateway{
		replies: replies,
	}
}

func (m *mockGateway) ChatStream(ctx context.Context, req *protocol.ChatRequest) (<-chan protocol.ChatResponse, error) {
	m.mu.Lock()
	m.requests = append(m.requests, req)
	idx := m.callIdx
	m.callIdx++
	m.mu.Unlock()

	reply := "Default reply"
	if idx < len(m.replies) {
		reply = m.replies[idx]
	}

	ch := make(chan protocol.ChatResponse, 8)
	go func() {
		defer close(ch)

		// 模拟流式切词分片下发
		parts := strings.Split(reply, " ")
		for i, part := range parts {
			delta := part
			if i < len(parts)-1 {
				delta += " "
			}
			ch <- protocol.ChatResponse{Delta: delta}
		}

		ch <- protocol.ChatResponse{
			Done: true,
			Usage: &protocol.Usage{
				PromptTokens:     10,
				CompletionTokens: 5,
				TotalTokens:      15,
			},
		}
	}()

	return ch, nil
}

func (m *mockGateway) TotalUsage() protocol.Usage {
	return protocol.Usage{TotalTokens: 15}
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
	var usage1 *protocol.Usage

	for ev := range stream1 {
		if ev.Type == protocol.EventError {
			t.Fatalf("turn 1 unexpected error: %s", ev.Error)
		}
		if ev.Type == protocol.EventDelta {
			text1.WriteString(ev.Delta)
		}
		if ev.Type == protocol.EventDone {
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
	if history1[0].Role != protocol.RoleUser || history1[0].Content != "Hello, my name is Coustea." {
		t.Errorf("unexpected history[0]: %+v", history1[0])
	}
	if history1[1].Role != protocol.RoleAssistant || history1[1].Content != "Hello! Nice to meet you, Coustea." {
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
	if req2.Messages[0].Role != protocol.RoleSystem {
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

func (b *blockingGateway) ChatStream(ctx context.Context, req *protocol.ChatRequest) (<-chan protocol.ChatResponse, error) {
	ch := make(chan protocol.ChatResponse, 2)
	go func() {
		defer close(ch)
		<-b.blockCh
		ch <- protocol.ChatResponse{Delta: "Done", Done: true}
	}()
	return ch, nil
}

func (b *blockingGateway) TotalUsage() protocol.Usage {
	return protocol.Usage{}
}

// 测试边界校验与空参数
func TestCoreAgent_Validation(t *testing.T) {
	// nil 网关表示未就绪内核：允许装配，但发起对话须给出配置引导
	unready, err := NewAgent(nil)
	if err != nil {
		t.Fatalf("expected nil gateway to assemble an unready agent, got: %v", err)
	}
	if _, err := unready.StreamRun(context.Background(), "hello"); err == nil || !strings.Contains(err.Error(), "no model gateway") {
		t.Errorf("expected unready agent StreamRun to fail with configuration guidance, got: %v", err)
	}

	ag, _ := NewAgent(&mockGateway{}, WithMemory(memory.NewSlidingWindowMemory(10)), WithMaxSteps(5))
	_, err = ag.StreamRun(context.Background(), "   ")
	if !errors.Is(err, ErrEmptyPrompt) {
		t.Errorf("expected ErrEmptyPrompt, got: %v", err)
	}
}

// 测试远程厂商缺密钥时仍装配出未就绪内核，供 /model 向导补齐密钥后热装网关
func TestNewFromConfig_RemoteWithoutKey_Unready(t *testing.T) {
	cfg := &config.Config{
		Provider:  config.ProviderDeepSeek,
		BaseURL:   config.DeepSeekBaseURL,
		ModelName: config.DefaultDeepSeekModel,
	}
	cfgPath := filepath.Join(t.TempDir(), "unready_config.json")

	ag, err := NewFromConfig(cfg, WithConfig(cfg, cfgPath))
	if err != nil {
		t.Fatalf("expected unready assembly without error, got: %v", err)
	}
	if ag.Config().HasAPIKey {
		t.Errorf("expected remote provider without key to be unready")
	}
	if _, err := ag.StreamRun(context.Background(), "hello"); err == nil {
		t.Errorf("expected StreamRun to fail before gateway is attached")
	}

	// 模拟 /model 向导补齐密钥：热装网关后恢复就绪
	if err := ag.UpdateConfig(string(config.ProviderDeepSeek), "sk-test-key", config.DefaultDeepSeekModel); err != nil {
		t.Fatalf("expected UpdateConfig to attach gateway, got: %v", err)
	}
	if !ag.Config().HasAPIKey {
		t.Errorf("expected agent to become ready after key configured")
	}
}

type toolCallStepGateway struct {
	mu    sync.Mutex
	steps []func(req *protocol.ChatRequest) []protocol.ChatResponse
	calls int
}

func (m *toolCallStepGateway) ChatStream(ctx context.Context, req *protocol.ChatRequest) (<-chan protocol.ChatResponse, error) {
	m.mu.Lock()
	idx := m.calls
	m.calls++
	m.mu.Unlock()

	ch := make(chan protocol.ChatResponse, 4)
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

func (m *toolCallStepGateway) TotalUsage() protocol.Usage {
	return protocol.Usage{}
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
		steps: []func(req *protocol.ChatRequest) []protocol.ChatResponse{
			// Step 1: 模型返回工具调用
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				if len(req.Tools) != 1 || req.Tools[0].Name != "adder" {
					t.Errorf("expected 1 tool 'adder' in request, got %v", req.Tools)
				}
				return []protocol.ChatResponse{
					{
						ToolCalls: []protocol.ToolCall{
							{
								ID:        "call_123",
								Name:      "adder",
								Arguments: `{"a": 2, "b": 3}`,
							},
						},
						Done: true,
					},
				}
			},
			// Step 2: 模型收到工具结果后生成最终文本答复
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				// 验证上下文历史中已经包含了 RoleTool
				lastMsg := req.Messages[len(req.Messages)-1]
				if lastMsg.Role != protocol.RoleTool || lastMsg.ToolResult == nil || lastMsg.ToolResult.IsError {
					t.Errorf("expected successful RoleTool message, got: %+v", lastMsg)
				}
				return []protocol.ChatResponse{
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

	var events []protocol.Event
	for ev := range stream {
		events = append(events, ev)
	}

	// 验证关键事件流：ToolCallStart -> ToolCallResult -> TextDelta -> Done
	var hasToolStart, hasToolResult, hasDone bool
	var finalAnswer strings.Builder

	for _, ev := range events {
		switch ev.Type {
		case protocol.EventToolCallStart:
			hasToolStart = true
			if ev.ToolCall.Name != "adder" {
				t.Errorf("unexpected tool call: %v", ev.ToolCall)
			}
		case protocol.EventToolCallResult:
			hasToolResult = true
			if ev.ToolResult.IsError {
				t.Errorf("tool execution failed unexpectedly: %v", ev.ToolResult.Content)
			}
		case protocol.EventDelta:
			finalAnswer.WriteString(ev.Delta)
		case protocol.EventDone:
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
		steps: []func(req *protocol.ChatRequest) []protocol.ChatResponse{
			// Step 1: 模型传入非法负数参数触发工具报错
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{
						ToolCalls: []protocol.ToolCall{
							{
								ID:        "call_neg",
								Name:      "adder",
								Arguments: `{"a": -5, "b": 3}`,
							},
						},
						Done: true,
					},
				}
			},
			// Step 2: 模型收到错误 Observation，进行自愈回答
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				lastMsg := req.Messages[len(req.Messages)-1]
				if lastMsg.Role != protocol.RoleTool || lastMsg.ToolResult == nil || !lastMsg.ToolResult.IsError {
					t.Errorf("expected RoleTool with IsError=true, got: %+v", lastMsg)
				}
				return []protocol.ChatResponse{
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
		if ev.Type == protocol.EventToolCallResult && ev.ToolResult.IsError {
			errorObsSeen = true
		}
		if ev.Type == protocol.EventDelta {
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
		steps: []func(req *protocol.ChatRequest) []protocol.ChatResponse{
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{
						ToolCalls: []protocol.ToolCall{
							{ID: "c1", Name: "adder", Arguments: `{"a":1,"b":1}`},
						},
						Done: true,
					},
				}
			},
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{
						ToolCalls: []protocol.ToolCall{
							{ID: "c2", Name: "adder", Arguments: `{"a":1,"b":1}`},
						},
						Done: true,
					},
				}
			},
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{
						ToolCalls: []protocol.ToolCall{
							{ID: "c3", Name: "adder", Arguments: `{"a":1,"b":1}`},
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
		if ev.Type == protocol.EventError && strings.Contains(ev.Error, ErrMaxSteps.Error()) {
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

	// 3. 显式覆盖 WithSystemPrompt：自定义 persona 生效，长期记忆块仍动态追加
	agCustomPrompt, err := NewAgent(gw, WithSystemPrompt("Explicit custom prompt"))
	if err != nil {
		t.Fatalf("failed to create agent with custom prompt: %v", err)
	}
	customPrompt := agCustomPrompt.SystemPrompt()
	if !strings.HasPrefix(customPrompt, "Explicit custom prompt") {
		t.Errorf("expected custom persona prefix, got: %s", customPrompt)
	}
	if strings.Contains(customPrompt, "general-purpose local AI personal assistant") {
		t.Errorf("expected default persona to be replaced, got: %s", customPrompt)
	}
	if !strings.Contains(customPrompt, "Long-Term Memory") {
		t.Errorf("expected long-term memory block to still be appended, got: %s", customPrompt)
	}
}

// 测试 P1：运行期沉淀的长期记忆在下一轮对话开始时即时注入系统提示词（每轮刷新）
func TestCoreAgent_LongTermMemory_RefreshedPerTurn(t *testing.T) {
	workDir := t.TempDir()
	gw := newMockGateway("reply one", "reply two")

	ag, err := NewAgent(gw, WithWorkDir(workDir))
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	ctx := context.Background()

	// 第一轮：记忆库此时尚无该内容
	stream1, err := ag.StreamRun(ctx, "first turn")
	if err != nil {
		t.Fatalf("turn 1 StreamRun failed: %v", err)
	}
	for range stream1 {
	}

	// 模拟模型在会话期间通过 write_file 沉淀长期记忆
	memFile := filepath.Join(workDir, ".coustea", "memory", memory.FileLearnings)
	if err := os.WriteFile(memFile, []byte("MAGIC_LONG_TERM_MEMORY_TOKEN"), 0o644); err != nil {
		t.Fatalf("failed to write memory file: %v", err)
	}

	// 第二轮：新沉淀的记忆应已出现在本轮系统提示词中
	stream2, err := ag.StreamRun(ctx, "second turn")
	if err != nil {
		t.Fatalf("turn 2 StreamRun failed: %v", err)
	}
	for range stream2 {
	}

	gw.mu.Lock()
	reqs := append([]*protocol.ChatRequest(nil), gw.requests...)
	gw.mu.Unlock()

	if len(reqs) != 2 {
		t.Fatalf("expected 2 gateway requests, got %d", len(reqs))
	}

	turn1System := reqs[0].Messages[0]
	if turn1System.Role != protocol.RoleSystem {
		t.Fatalf("expected first message to be system, got %s", turn1System.Role)
	}
	if strings.Contains(turn1System.Content, "MAGIC_LONG_TERM_MEMORY_TOKEN") {
		t.Errorf("turn 1 system prompt should not contain memory written afterwards")
	}

	turn2System := reqs[1].Messages[0]
	if turn2System.Role != protocol.RoleSystem {
		t.Fatalf("expected first message to be system, got %s", turn2System.Role)
	}
	if !strings.Contains(turn2System.Content, "MAGIC_LONG_TERM_MEMORY_TOKEN") {
		t.Errorf("turn 2 system prompt should contain memory written in the previous turn, got: %s", turn2System.Content)
	}
}

// 测试权限策略确实作为执行前钩子在装配期挂载到了工具执行流水线上：
// 破坏性 bash 命令被拦截、不会真正执行，且拒绝文案原样回灌给模型。
func TestCoreAgent_PermissionHook_Mounted(t *testing.T) {
	gw := &toolCallStepGateway{
		steps: []func(req *protocol.ChatRequest) []protocol.ChatResponse{
			// Step 1: 模型请求执行破坏性命令
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{
						ToolCalls: []protocol.ToolCall{
							{ID: "call_1", Name: "bash", Arguments: `{"command": "rm -rf /"}`},
						},
						Done: true,
					},
				}
			},
			// Step 2: 断言模型收到的是策略拒绝的精确文案，而非被泛化的「执行错误」
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				if len(req.Messages) == 0 {
					t.Errorf("expected a non-empty message history")
					return []protocol.ChatResponse{{Delta: "blocked"}, {Done: true}}
				}
				last := req.Messages[len(req.Messages)-1]
				if last.Role != protocol.RoleTool || last.ToolResult == nil {
					t.Errorf("expected a RoleTool message, got %+v", last)
					return []protocol.ChatResponse{{Delta: "blocked"}, {Done: true}}
				}
				if !last.ToolResult.IsError {
					t.Errorf("expected the blocked command to be reported as an error")
				}
				if !strings.Contains(last.ToolResult.Content, "blocked by Gate 1 (Hard Deny)") {
					t.Errorf("expected the precise Gate 1 hard deny message to reach the model, got %q", last.ToolResult.Content)
				}
				if strings.Contains(last.ToolResult.Content, "Tool execution error") {
					t.Errorf("policy message was overwritten by the generic error text: %q", last.ToolResult.Content)
				}
				return []protocol.ChatResponse{{Delta: "Blocked."}, {Done: true}}
			},
		},
	}

	ag, err := NewAgent(gw, WithDefaultTools())
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	stream, err := ag.StreamRun(context.Background(), "please clean up the disk")
	if err != nil {
		t.Fatalf("StreamRun failed: %v", err)
	}
	for range stream {
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

// 测试基于 Harness 思想的流式三道闸门交互审批流程 (Gate 3 用户审批与拒绝自愈)
func TestCoreAgent_PermissionPipeline_InteractiveApproval(t *testing.T) {
	tmpDir := t.TempDir()

	// 1. 测试允许流程 (AllowOnce)
	gwAllow := &toolCallStepGateway{
		steps: []func(req *protocol.ChatRequest) []protocol.ChatResponse{
			// Step 1: 模型发起命令调用
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{
						ToolCalls: []protocol.ToolCall{
							{ID: "call_bash_1", Name: "bash", Arguments: `{"command": "rm -f 'harness_approval_test.tmp' && echo 'harness_approval_test'"}`},
						},
						Done: true,
					},
				}
			},
			// Step 2: 模型接收到工具执行输出并生成最终回复
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				last := req.Messages[len(req.Messages)-1]
				if last.Role != protocol.RoleTool || last.ToolResult == nil {
					t.Fatalf("expected RoleTool message, got: %+v", last)
				}
				if last.ToolResult.IsError {
					t.Fatalf("expected tool call to succeed, got error: %s", last.ToolResult.Content)
				}
				if !strings.Contains(last.ToolResult.Content, "harness_approval_test") {
					t.Errorf("expected tool output to contain 'harness_approval_test', got: %s", last.ToolResult.Content)
				}
				return []protocol.ChatResponse{{Delta: "Done executed."}, {Done: true}}
			},
		},
	}

	agAllow, err := NewAgent(gwAllow, WithWorkDir(tmpDir), WithDefaultTools())
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	streamAllow, err := agAllow.StreamRun(context.Background(), "Run test command")
	if err != nil {
		t.Fatalf("StreamRun failed: %v", err)
	}

	permissionPromptReceived := false
	for ev := range streamAllow {
		if ev.Type == protocol.EventPermissionReq && ev.Permission != nil {
			permissionPromptReceived = true
			if ev.Permission.ToolName != "bash" {
				t.Errorf("expected permission tool name 'bash', got %s", ev.Permission.ToolName)
			}
			// 模拟用户在终端同意执行
			_ = agAllow.RespondPermission(ev.Permission.RequestID, protocol.DecisionAllowOnce)
		}
	}

	if !permissionPromptReceived {
		t.Errorf("expected to receive EventToolPermissionRequest in stream")
	}

	// 2. 测试拒绝流程 (User Deny -> Error as Observation)
	gwDeny := &toolCallStepGateway{
		steps: []func(req *protocol.ChatRequest) []protocol.ChatResponse{
			// Step 1: 模型发起命令调用
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				return []protocol.ChatResponse{
					{
						ToolCalls: []protocol.ToolCall{
							{ID: "call_bash_2", Name: "bash", Arguments: `{"command": "rm -f 'harness_approval_test.tmp' && echo 'will_be_denied'"}`},
						},
						Done: true,
					},
				}
			},
			// Step 2: 模型接收到人类拒绝的观察结果，完成自愈回复
			func(req *protocol.ChatRequest) []protocol.ChatResponse {
				last := req.Messages[len(req.Messages)-1]
				if last.Role != protocol.RoleTool || last.ToolResult == nil {
					t.Fatalf("expected RoleTool message, got: %+v", last)
				}
				if !last.ToolResult.IsError {
					t.Fatalf("expected tool result to be error due to user denial")
				}
				if !strings.Contains(last.ToolResult.Content, "permission denied by user") {
					t.Errorf("expected content to mention permission denied by user, got: %s", last.ToolResult.Content)
				}
				return []protocol.ChatResponse{{Delta: "Understood, command was cancelled by user."}, {Done: true}}
			},
		},
	}

	agDeny, err := NewAgent(gwDeny, WithWorkDir(tmpDir), WithDefaultTools())
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	streamDeny, err := agDeny.StreamRun(context.Background(), "Run command to deny")
	if err != nil {
		t.Fatalf("StreamRun failed: %v", err)
	}

	permissionDenyReceived := false
	for ev := range streamDeny {
		if ev.Type == protocol.EventPermissionReq && ev.Permission != nil {
			permissionDenyReceived = true
			// 模拟用户在终端拒绝执行
			_ = agDeny.RespondPermission(ev.Permission.RequestID, protocol.DecisionDeny)
		}
	}

	if !permissionDenyReceived {
		t.Errorf("expected to receive EventToolPermissionRequest in deny stream")
	}
}

func TestAgent_ConfigAndModelSwitching(t *testing.T) {
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "test_config.json")

	cfg := &config.Config{
		Provider:  config.ProviderLlamaCpp,
		ModelName: config.DefaultLlamaCppModel,
		BaseURL:   config.DefaultLlamaCppBaseURL,
		Providers: make(map[string]config.ProviderConfig),
	}

	ag, err := NewFromConfig(cfg, WithConfig(cfg, cfgPath), WithWorkDir(tmpDir))
	if err != nil {
		t.Fatalf("failed to create agent from config: %v", err)
	}

	// 1. 验证 Config() 包含结构化 Providers 与推荐模型
	cv := ag.Config()
	if len(cv.Providers) < 4 {
		t.Fatalf("expected at least 4 providers in ConfigView, got %d", len(cv.Providers))
	}
	var llamaP, geminiP, dsP *protocol.ProviderInfo
	for i := range cv.Providers {
		p := &cv.Providers[i]
		if p.ID == "llamacpp" {
			llamaP = p
		} else if p.ID == "gemini" {
			geminiP = p
		} else if p.ID == "deepseek" {
			dsP = p
		}
	}
	if llamaP == nil || !llamaP.IsLocal || !llamaP.IsConfigured {
		t.Errorf("unexpected llamaP info: %+v", llamaP)
	}
	if geminiP == nil || geminiP.IsConfigured {
		t.Errorf("expected geminiP initially not configured, got: %+v", geminiP)
	}
	if len(geminiP.RecommendedModels) < 2 {
		t.Errorf("expected recommended models for gemini, got: %+v", geminiP.RecommendedModels)
	}
	if dsP == nil || dsP.IsConfigured || len(dsP.RecommendedModels) < 3 {
		t.Errorf("unexpected dsP info: %+v", dsP)
	}

	// 2. 配置 Gemini 平台与密钥
	if err := ag.UpdateConfig("gemini", "sk-gemini-test-secret", "gemini-2.5-flash"); err != nil {
		t.Fatalf("failed to update gemini config: %v", err)
	}
	cv = ag.Config()
	if cv.Provider != "gemini" || cv.ModelName != "gemini-2.5-flash" || !cv.HasAPIKey {
		t.Fatalf("unexpected cv after gemini update: %+v", cv)
	}

	// 3. 尝试直接通过模型名 "deepseek-reasoner" 切换：因 deepseek 尚未配置密钥，预期返回失败
	if err := ag.UpdateConfig("", "", "deepseek-reasoner"); err == nil {
		t.Fatalf("expected error when switching to unconfigured deepseek model, got nil")
	}

	// 4. 配置 DeepSeek 密钥
	if err := ag.UpdateConfig("deepseek", "sk-deepseek-test-secret", "deepseek-flash"); err != nil {
		t.Fatalf("failed to update deepseek config: %v", err)
	}

	// 5. 再次通过模型名 "deepseek-reasoner" 智能推断切模：已保存密钥，预期成功！
	if err := ag.UpdateConfig("", "", "deepseek-reasoner"); err != nil {
		t.Fatalf("expected success with model inference for deepseek-reasoner, got: %v", err)
	}
	cv = ag.Config()
	if cv.Provider != "deepseek" || cv.ModelName != "deepseek-reasoner" {
		t.Fatalf("expected deepseek and deepseek-reasoner, got: %+v", cv)
	}

	// 6. 切换回 Gemini 并更改模型为 "gemini-2.5-pro"，无需重新提供 API Key (自动复用)
	if err := ag.UpdateConfig("gemini", "", "gemini-2.5-pro"); err != nil {
		t.Fatalf("expected success reusing saved gemini key, got: %v", err)
	}
	cv = ag.Config()
	if cv.Provider != "gemini" || cv.ModelName != "gemini-2.5-pro" {
		t.Fatalf("expected gemini and gemini-2.5-pro, got: %+v", cv)
	}
}

// TestCoreAgent_DirectToolExecute_PermissionHook 验证装配期钩子在脱离循环本体时依然生效
func TestCoreAgent_DirectToolExecute_PermissionHook(t *testing.T) {
	mockGW := newMockGateway("hi")
	ag, err := NewAgent(mockGW, WithDefaultTools())
	if err != nil {
		t.Fatalf("NewAgent failed: %v", err)
	}

	res := ag.tools.Execute(context.Background(), protocol.ToolCall{
		ID:        "direct_call_1",
		Name:      "bash",
		Arguments: `{"command": "rm -rf /"}`,
	})
	if !res.IsError || !strings.Contains(res.Content, "blocked by Gate 1 (Hard Deny)") {
		t.Fatalf("expected Gate 1 hard deny error in ToolResult, got: %+v", res)
	}
}

type simpleTestTool struct {
	name string
	fn   func(ctx context.Context, args json.RawMessage) (string, error)
}

func (s *simpleTestTool) Name() string            { return s.name }
func (s *simpleTestTool) Description() string     { return "test tool" }
func (s *simpleTestTool) Schema() json.RawMessage { return json.RawMessage(`{"type":"object"}`) }
func (s *simpleTestTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	return s.fn(ctx, args)
}

// TestCoreAgent_LargeToolResult_Persisted 验证大输出经 PostToolUse 钩子被落盘且截断为预览
func TestCoreAgent_LargeToolResult_Persisted(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "coustea-posthook-test-*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	mockGW := newMockGateway("hi")
	ag, err := NewAgent(mockGW, WithWorkDir(tmpDir))
	if err != nil {
		t.Fatalf("NewAgent failed: %v", err)
	}

	largeContent := strings.Repeat("A", 10000)
	ag.tools.Register(&simpleTestTool{
		name: "large_tool",
		fn: func(ctx context.Context, args json.RawMessage) (string, error) {
			return largeContent, nil
		},
	})

	res := ag.tools.Execute(context.Background(), protocol.ToolCall{
		ID:        "large_call_1",
		Name:      "large_tool",
		Arguments: `{}`,
	})

	if !strings.Contains(res.Content, "[output truncated: 10000 characters total; full content saved to") {
		t.Fatalf("expected truncated notice in res.Content, got: %s", res.Content)
	}

	// 验证磁盘文件确实写入且内容为全量
	savedPath := filepath.Join(tmpDir, ".coustea", "tool-results", "large_call_1.txt")
	data, err := os.ReadFile(savedPath)
	if err != nil {
		t.Fatalf("expected tool result file to exist at %s, got: %v", savedPath, err)
	}
	if string(data) != largeContent {
		t.Fatalf("expected full content in file, length was %d", len(data))
	}
}
