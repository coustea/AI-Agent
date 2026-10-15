package tui

import (
	"context"
	"encoding/json"
	"os"
	"strings"
	"testing"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/gateway"
	"my-agent/internal/permission"

	tea "github.com/charmbracelet/bubbletea"
)

func TestTUIFlow(t *testing.T) {
	testCfgPath := "test_config.json"
	defer os.Remove(testCfgPath)

	t.Setenv("DEEPSEEK_API_KEY", "")
	t.Setenv("GEMINI_API_KEY", "")
	t.Setenv("GOOGLE_API_KEY", "")

	m := NewModel(nil)
	m.cfgPath = testCfgPath

	// 1. 验证主线设计：初始状态必须直接是对话页面（输入框交互）
	if m.state != stateChat {
		t.Fatalf("expected initial mainline state to be stateChat, got %v", m.state)
	}

	// 2. 验证主线对话交互：发送普通消息实时在界面展示
	m.chatInput.SetValue("Hello coustea, this is mainline chat!")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if len(m.messages) == 0 {
		t.Fatalf("expected messages to have content")
	}
	lastUserMsg := m.messages[len(m.messages)-2]
	if lastUserMsg.Sender != "You" || lastUserMsg.Content != "Hello coustea, this is mainline chat!" {
		t.Fatalf("expected user message to be recorded in chat history, got: %+v", lastUserMsg)
	}

	m.isGenerating = false

	// 3. 验证支线触发：在输入框输入 /model 调出模型配置向导
	m.chatInput.SetValue("/model")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateSelectModel {
		t.Fatalf("expected state to switch to stateSelectModel after /model, got %v", m.state)
	}

	// 4. 模拟在支线选择列表中选择 DeepSeek (下移一行并回车)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)
	if m.cursor != 1 {
		t.Fatalf("expected cursor to be 1 (ds), got %d", m.cursor)
	}

	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 5. 验证进入 API Key 输入
	if m.state != stateInputAPIKey {
		t.Fatalf("expected stateInputAPIKey, got %v", m.state)
	}
	if m.config.Provider != config.ProviderDeepSeek {
		t.Fatalf("expected provider %q, got %q", config.ProviderDeepSeek, m.config.Provider)
	}

	m.apiKeyInput.SetValue("sk-test-key-123456")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 6. 验证进入模型名称输入，且默认填入最新的 Flash 模型 (deepseek-flash)
	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel, got %v", m.state)
	}
	if m.config.ModelName != config.DefaultDeepSeekModel {
		t.Fatalf("expected default flash model %s, got %s", config.DefaultDeepSeekModel, m.config.ModelName)
	}

	// 回车确认保存
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 7. 验证支线配置完成后自动无缝回到主线对话页面
	if m.state != stateChat {
		t.Fatalf("expected state to return to stateChat, got %v", m.state)
	}

	// 验证配置文件已被持久化到 JSON
	savedCfg, err := config.LoadConfig(testCfgPath)
	if err != nil {
		t.Fatalf("failed to load saved config: %v", err)
	}
	if savedCfg.APIKey != "sk-test-key-123456" || savedCfg.ModelName != config.DefaultDeepSeekModel {
		t.Fatalf("saved config mismatch: %+v", savedCfg)
	}

	// 8. 验证 View 渲染正常
	viewOutput := m.View()
	if viewOutput == "" {
		t.Fatalf("expected non-empty view output")
	}
}

func TestTUIToolEventRendering(t *testing.T) {
	m := NewModel(nil)
	m.messages = append(m.messages, ChatMessage{
		Sender:  "coustea",
		Content: "Thinking...",
	})

	// 1. 模拟收到 EventToolCallStart
	mIntf, _ := m.Update(agentStreamEventMsg{
		event: agent.AgentEvent{
			Type: agent.EventToolCallStart,
			ToolCall: &gateway.ToolCall{
				ID:        "call_1",
				Name:      "read_file",
				Arguments: []byte(`{"path": "sample.go"}`),
			},
		},
	})
	m = mIntf.(Model)

	lastContent := m.messages[len(m.messages)-1].Content
	if !strings.Contains(lastContent, "read_file") || !strings.Contains(lastContent, "sample.go") {
		t.Errorf("expected tool call to be rendered in content, got: %s", lastContent)
	}

	// 2. 模拟收到 EventToolCallResult
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: agent.AgentEvent{
			Type: agent.EventToolCallResult,
			ToolResult: &gateway.ToolResult{
				ToolCallID: "call_1",
				Name:       "read_file",
				Content:    "package main\nfunc main() {}",
				IsError:    false,
			},
		},
	})
	m = mIntf.(Model)

	lastContent = m.messages[len(m.messages)-1].Content
	if !strings.Contains(lastContent, "package main") {
		t.Errorf("expected tool result to be rendered in content, got: %s", lastContent)
	}

	// 3. 验证 View 渲染正常不崩溃
	rendered := m.View()
	if !strings.Contains(rendered, "read_file") {
		t.Errorf("rendered view missing tool info: %s", rendered)
	}
}

type mockTuiGateway struct {
	replies []string
	callIdx int
}

func (m *mockTuiGateway) Chat(ctx context.Context, req *gateway.ChatRequest) (*gateway.ChatResponse, error) {
	return nil, nil
}

func (m *mockTuiGateway) ChatStream(ctx context.Context, req *gateway.ChatRequest) (<-chan gateway.StreamChunk, error) {
	reply := "Default reply"
	if m.callIdx < len(m.replies) {
		reply = m.replies[m.callIdx]
	}
	m.callIdx++

	ch := make(chan gateway.StreamChunk, 4)
	go func() {
		defer close(ch)
		ch <- gateway.StreamChunk{Delta: reply}
		ch <- gateway.StreamChunk{Done: true, Usage: &gateway.Usage{TotalTokens: 20}}
	}()
	return ch, nil
}

func (m *mockTuiGateway) TotalUsage() gateway.Usage {
	return gateway.Usage{}
}

func TestTUI_EndToEnd_MultiTurn_Chat(t *testing.T) {
	gw := &mockTuiGateway{
		replies: []string{
			"Hello Alice! Nice to meet you.",
			"Your name is Alice.",
		},
	}
	ag, err := agent.NewAgent(gw)
	if err != nil {
		t.Fatalf("failed to create agent: %v", err)
	}

	m := NewModel(ag)

	// ====== 轮次 1 ======
	m.chatInput.SetValue("My name is Alice")
	mIntf, cmd := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 执行 Cmd 驱动事件流
	for cmd != nil {
		msg := cmd()
		mIntf, cmd = m.Update(msg)
		m = mIntf.(Model)
	}

	if m.isGenerating {
		t.Errorf("expected isGenerating to be false after stream complete")
	}

	lastMsg := m.messages[len(m.messages)-1]
	if lastMsg.Sender != "coustea" || !strings.Contains(lastMsg.Content, "Hello Alice") {
		t.Errorf("turn 1 unexpected assistant reply: %+v", lastMsg)
	}

	// ====== 轮次 2 ======
	m.chatInput.SetValue("What is my name?")
	mIntf, cmd = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	for cmd != nil {
		msg := cmd()
		mIntf, cmd = m.Update(msg)
		m = mIntf.(Model)
	}

	lastMsg = m.messages[len(m.messages)-1]
	if lastMsg.Sender != "coustea" || !strings.Contains(lastMsg.Content, "Your name is Alice") {
		t.Errorf("turn 2 unexpected assistant reply: %+v", lastMsg)
	}

	// 验证 View 渲染出两轮对话
	view := m.View()
	if !strings.Contains(view, "My name is Alice") || !strings.Contains(view, "Your name is Alice") {
		t.Errorf("view missing expected conversation content:\n%s", view)
	}
}

func TestTUIFlow_Gemini(t *testing.T) {
	testCfgPath := "test_gemini_config.json"
	defer os.Remove(testCfgPath)

	t.Setenv("DEEPSEEK_API_KEY", "")
	t.Setenv("GEMINI_API_KEY", "")
	t.Setenv("GOOGLE_API_KEY", "")

	m := NewModel(nil)
	m.cfgPath = testCfgPath

	// 触发 /model
	m.chatInput.SetValue("/model")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 下移两次选择 Gemini (第 3 项，索引 2)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)

	if m.cursor != 2 {
		t.Fatalf("expected cursor to be 2 for gemini, got %d", m.cursor)
	}

	// 回车选中
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputAPIKey {
		t.Fatalf("expected stateInputAPIKey, got %v", m.state)
	}
	if m.config.Provider != config.ProviderGemini {
		t.Fatalf("expected provider %q, got %q", config.ProviderGemini, m.config.Provider)
	}

	// 输入 APIKey
	m.apiKeyInput.SetValue("sk-gemini-test-secret")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel, got %v", m.state)
	}
	if m.config.ModelName != config.DefaultGeminiModel {
		t.Fatalf("expected default gemini model %s, got %s", config.DefaultGeminiModel, m.config.ModelName)
	}

	// 回车保存
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat, got %v", m.state)
	}

	savedCfg, err := config.LoadConfig(testCfgPath)
	if err != nil {
		t.Fatalf("failed to load saved config: %v", err)
	}
	if savedCfg.Provider != config.ProviderGemini || savedCfg.ModelName != config.DefaultGeminiModel || savedCfg.APIKey != "sk-gemini-test-secret" {
		t.Fatalf("saved config mismatch: %+v", savedCfg)
	}
}

// 测试模型切换时无需重新输入已保存的密钥
func TestTUIFlow_SwitchWithoutReenteringAPIKey(t *testing.T) {
	testCfgPath := "test_switch_config.json"
	defer os.Remove(testCfgPath)

	// 初始状态配置好 DeepSeek
	initialCfg := &config.Config{
		Provider:  config.ProviderDeepSeek,
		BaseURL:   config.DeepSeekBaseURL,
		ModelName: config.DefaultDeepSeekModel,
		APIKey:    "sk-deepseek-preserved-key",
	}
	if err := config.SaveConfig(testCfgPath, initialCfg); err != nil {
		t.Fatalf("failed to setup initial config: %v", err)
	}

	m := NewModel(nil)
	m.cfgPath = testCfgPath
	m.config = *initialCfg
	for i, c := range m.choices {
		if strings.EqualFold(c, string(m.config.Provider)) {
			m.selected = i
			m.cursor = i
			break
		}
	}

	// 1. 切换到 Gemini 并配置
	m.chatInput.SetValue("/model")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 当前在 DeepSeek (索引 1)，下移一次选择 Gemini (索引 2)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 输入 Gemini Key 并保存
	m.apiKeyInput.SetValue("sk-gemini-preserved-key")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.config.Provider != config.ProviderGemini {
		t.Fatalf("expected switched to gemini")
	}

	// 2. 再次通过 /model 切回 DeepSeek
	m.chatInput.SetValue("/model")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 当前在 Gemini (索引 2)，上移一次选中 DeepSeek (索引 1)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyUp})
	m = mIntf.(Model)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 此时应该检测到已保存的 DeepSeek key，无需重新输入，直接回车！
	if m.apiKeyInput.Value() != "sk-deepseek-preserved-key" {
		t.Errorf("expected apiKeyInput to be prefilled with preserved key, got %s", m.apiKeyInput.Value())
	}

	// 直接按 Enter 保留已有 key
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 直接按 Enter 保留默认模型
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat, got %v", m.state)
	}

	// 验证最终切回的配置完美保持原 key
	if m.config.Provider != config.ProviderDeepSeek || m.config.APIKey != "sk-deepseek-preserved-key" {
		t.Fatalf("expected deepseek with preserved key, got %+v", m.config)
	}
}

// 测试键盘按键操作：退出 (Ctrl+C, Ctrl+D, /exit, /quit, /q) 以及生成中断 (Ctrl+C, Esc)
func TestTUI_KeyOperations_ExitAndInterrupt(t *testing.T) {
	m := NewModel(nil)

	// 1. 空闲聊天状态下按 Ctrl+C 直接退出
	_, cmd := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	if cmd == nil {
		t.Fatalf("expected tea.Quit command on Ctrl+C, got nil")
	}

	// 2. 空闲聊天状态且输入框为空时按 Ctrl+D 退出
	_, cmd = m.Update(tea.KeyMsg{Type: tea.KeyCtrlD})
	if cmd == nil {
		t.Fatalf("expected tea.Quit command on Ctrl+D, got nil")
	}

	// 3. 输入快捷命令 /exit, /quit, /q 退出
	for _, cmdStr := range []string{"/exit", "/quit", "/q"} {
		m.chatInput.SetValue(cmdStr)
		_, cmd = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
		if cmd == nil {
			t.Fatalf("expected tea.Quit command on command %s, got nil", cmdStr)
		}
	}

	// 4. 在模型配置向导页面中按 Ctrl+C 退出
	m.state = stateSelectModel
	_, cmd = m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	if cmd == nil {
		t.Fatalf("expected tea.Quit on Ctrl+C in stateSelectModel, got nil")
	}

	m.state = stateInputAPIKey
	_, cmd = m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	if cmd == nil {
		t.Fatalf("expected tea.Quit on Ctrl+C in stateInputAPIKey, got nil")
	}

	m.state = stateInputModel
	_, cmd = m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	if cmd == nil {
		t.Fatalf("expected tea.Quit on Ctrl+C in stateInputModel, got nil")
	}

	// 5. 流式生成中按 Ctrl+C 或 Esc 触发中断当前生成而非直接退出应用
	m.state = stateChat
	m.isGenerating = true
	var cancelled bool
	m.cancel = func() { cancelled = true }
	m.messages = []ChatMessage{{Sender: "coustea", Content: "Thinking"}}

	mIntf, cmd := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	m = mIntf.(Model)

	if !cancelled {
		t.Errorf("expected cancel func to be executed on Ctrl+C while generating")
	}
	if m.isGenerating {
		t.Errorf("expected isGenerating to be false after interruption")
	}
	if cmd != nil {
		t.Errorf("expected no tea.Quit command during interruption, got: %v", cmd)
	}
	if !strings.Contains(m.messages[len(m.messages)-1].Content, "中断") {
		t.Errorf("expected interruption note in message, got: %s", m.messages[len(m.messages)-1].Content)
	}
}

// 测试 TUI 界面对 Harness EventToolPermissionRequest 的交互响应与审批反馈
func TestTUI_PermissionApproval_InteractiveFlow(t *testing.T) {
	m := NewModel(nil)
	m.messages = []ChatMessage{{Sender: "coustea", Content: ""}}
	m.isGenerating = true

	var userDecision permission.Decision
	decisionChan := make(chan permission.Decision, 1)

	prompt := &agent.PermissionPrompt{
		Request: permission.Request{
			ToolCallID: "tc-test",
			ToolName:   "bash",
			Arguments:  json.RawMessage(`{"command":"rm -rf ./tmp"}`),
			Reason:     "potentially destructive shell command: rm -rf ./tmp",
		},
		Respond: func(d permission.Decision) {
			userDecision = d
			decisionChan <- d
		},
	}

	// 1. 模拟收到来自 Agent Harness 的流式权限审批请求
	eventMsg := agentStreamEventMsg{
		event: agent.AgentEvent{
			Type:             agent.EventToolPermissionRequest,
			PermissionPrompt: prompt,
		},
		ch: make(<-chan agent.AgentEvent),
	}

	mIntf, _ := m.Update(eventMsg)
	m = mIntf.(Model)

	if m.pendingPrompt == nil {
		t.Fatalf("expected pendingPrompt to be set upon EventToolPermissionRequest")
	}

	// 2. 验证界面视图中正确渲染出权限卡片
	viewText := m.View()
	if !strings.Contains(viewText, "权限审批 Gate 3") {
		t.Errorf("expected view to contain '权限审批 Gate 3', got:\n%s", viewText)
	}
	if !strings.Contains(viewText, "rm -rf ./tmp") {
		t.Errorf("expected view to contain command details, got:\n%s", viewText)
	}

	// 3. 用户在终端按下 'y' 键允许本次调用
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'y'}})
	m = mIntf.(Model)

	if m.pendingPrompt != nil {
		t.Errorf("expected pendingPrompt to be cleared after user approval")
	}

	select {
	case d := <-decisionChan:
		if d != permission.DecisionAllowOnce {
			t.Errorf("expected DecisionAllowOnce, got %v", d)
		}
	default:
		t.Errorf("expected Respond callback to be invoked with user decision")
	}
	if userDecision != permission.DecisionAllowOnce {
		t.Errorf("expected userDecision to be DecisionAllowOnce, got %v", userDecision)
	}
}
