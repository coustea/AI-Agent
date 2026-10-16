package tui

import (
	"context"
	"strings"
	"testing"

	"my-agent/internal/protocol"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/x/ansi"
)

// mockTestAgent 纯内存实现的智能体测试桩
type mockTestAgent struct {
	cfgView             protocol.ConfigView
	replies             []string
	replyIdx            int
	lastPermissionReqID string
	lastDecision        protocol.Decision
	memoryCount         int
	totalUsage          protocol.Usage
	updateConfigErr     error
}

func newMockAgent(replies ...string) *mockTestAgent {
	return &mockTestAgent{
		cfgView: protocol.ConfigView{
			Provider:           "llamacpp",
			ModelName:          "local-model",
			HasAPIKey:          true,
			AvailableProviders: []string{"llamacpp", "deepseek", "gemini", "spark"},
		},
		replies: replies,
	}
}

func (m *mockTestAgent) StreamRun(ctx context.Context, prompt string) (<-chan protocol.Event, error) {
	ch := make(chan protocol.Event, 4)
	reply := "Default reply"
	if m.replyIdx < len(m.replies) {
		reply = m.replies[m.replyIdx]
		m.replyIdx++
	}
	go func() {
		defer close(ch)
		ch <- protocol.Event{Type: protocol.EventDelta, Delta: reply}
		ch <- protocol.Event{Type: protocol.EventDone, Usage: &protocol.Usage{TotalTokens: 20}}
	}()
	return ch, nil
}

func (m *mockTestAgent) RespondPermission(reqID string, decision protocol.Decision) error {
	m.lastPermissionReqID = reqID
	m.lastDecision = decision
	return nil
}

func (m *mockTestAgent) Reset() {}

func (m *mockTestAgent) Config() protocol.ConfigView {
	return m.cfgView
}

func (m *mockTestAgent) UpdateConfig(provider, apiKey, model string) error {
	if m.updateConfigErr != nil {
		return m.updateConfigErr
	}
	m.cfgView.Provider = provider
	if apiKey != "" {
		m.cfgView.HasAPIKey = true
	}
	if model != "" {
		m.cfgView.ModelName = model
	}
	return nil
}

func (m *mockTestAgent) MemoryCount() int {
	return m.memoryCount
}

func (m *mockTestAgent) TotalUsage() protocol.Usage {
	return m.totalUsage
}

func (m *mockTestAgent) SystemPrompt() string { return "" }
func (m *mockTestAgent) WorkDir() string      { return "" }

func TestTUIFlow(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag)

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
	if m.currentProvider != "deepseek" {
		t.Fatalf("expected provider deepseek, got %q", m.currentProvider)
	}

	m.apiKeyInput.SetValue("sk-test-key-123456")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 6. 验证进入模型名称输入，且默认填入 deepseek-chat
	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel, got %v", m.state)
	}
	if m.currentModel != "deepseek-chat" {
		t.Fatalf("expected default deepseek-chat model, got %s", m.currentModel)
	}

	// 回车确认保存
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 7. 验证支线配置完成后自动无缝回到主线对话页面
	if m.state != stateChat {
		t.Fatalf("expected state to return to stateChat, got %v", m.state)
	}
	if ag.cfgView.Provider != "deepseek" || ag.cfgView.ModelName != "deepseek-chat" {
		t.Fatalf("agent config mismatch: %+v", ag.cfgView)
	}

	// 8. 验证 View 渲染正常
	viewOutput := m.View()
	if viewOutput == "" {
		t.Fatalf("expected non-empty view output")
	}
}

func TestTUIToolEventRendering(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag)
	m.messages = append(m.messages, ChatMessage{
		Sender:  "coustea",
		Content: "Thinking...",
	})

	// 1. 模拟收到 EventToolCallStart
	mIntf, _ := m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type: protocol.EventToolCallStart,
			ToolCall: &protocol.ToolCallRecord{
				ID:        "call_1",
				Name:      "read_file",
				Arguments: `{"path": "sample.go"}`,
			},
		},
	})
	m = mIntf.(Model)

	lastMsg := m.messages[len(m.messages)-1]
	if len(lastMsg.ToolCalls) == 0 || lastMsg.ToolCalls[0].Name != "read_file" {
		t.Fatalf("expected tool call to be recorded in ToolCalls, got: %+v", lastMsg.ToolCalls)
	}

	// 2. 模拟收到 EventToolCallResult
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type: protocol.EventToolCallResult,
			ToolResult: &protocol.ToolResultRecord{
				ToolCallID: "call_1",
				Name:       "read_file",
				Content:    "package main\nfunc main() {}",
				IsError:    false,
			},
		},
	})
	m = mIntf.(Model)

	lastMsg = m.messages[len(m.messages)-1]
	if len(lastMsg.ToolCalls) == 0 || lastMsg.ToolCalls[0].Running || !strings.Contains(lastMsg.ToolCalls[0].Result, "package main") {
		t.Fatalf("expected tool result to be recorded, got: %+v", lastMsg.ToolCalls)
	}

	// 3. 验证 View 渲染正常不崩溃
	rendered := m.View()
	if !strings.Contains(rendered, "read_file") {
		t.Errorf("rendered view missing tool info: %s", rendered)
	}
	if !strings.Contains(rendered, "package main") {
		t.Errorf("rendered view missing tool result: %s", rendered)
	}
}

func TestTUI_EndToEnd_MultiTurn_Chat(t *testing.T) {
	ag := newMockAgent(
		"Hello Alice! Nice to meet you.",
		"Your name is Alice.",
	)
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

	// 验证 View 渲染出两轮对话 (去除 ANSI 控制码后验证语义内容)
	strippedView := ansi.Strip(m.View())
	if !strings.Contains(strippedView, "My name is Alice") || !strings.Contains(strippedView, "Your name is Alice") {
		t.Errorf("view missing expected conversation content:\n%s", strippedView)
	}
}

func TestTUIFlow_Gemini(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag)

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
	if m.currentProvider != "gemini" {
		t.Fatalf("expected provider gemini, got %q", m.currentProvider)
	}

	// 输入 APIKey
	m.apiKeyInput.SetValue("sk-gemini-test-secret")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel, got %v", m.state)
	}
	if m.currentModel != "gemini-2.5-flash" {
		t.Fatalf("expected default gemini model gemini-2.5-flash, got %s", m.currentModel)
	}

	// 回车保存
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat, got %v", m.state)
	}
	if ag.cfgView.Provider != "gemini" || ag.cfgView.ModelName != "gemini-2.5-flash" {
		t.Fatalf("agent config mismatch: %+v", ag.cfgView)
	}
}

// 测试模型切换流程
func TestTUIFlow_SwitchWithoutReenteringAPIKey(t *testing.T) {
	ag := newMockAgent()
	ag.cfgView.Provider = "deepseek"
	ag.cfgView.ModelName = "deepseek-chat"

	m := NewModel(ag)
	m.currentAPIKey = "sk-deepseek-preserved-key"

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

	if ag.cfgView.Provider != "gemini" {
		t.Fatalf("expected switched to gemini, got %s", ag.cfgView.Provider)
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

	// 直接按 Enter 保留已有 key
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 直接按 Enter 保留默认模型
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat, got %v", m.state)
	}
	if ag.cfgView.Provider != "deepseek" {
		t.Fatalf("expected deepseek, got %+v", ag.cfgView)
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

// 测试 TUI 界面对 Harness EventPermissionReq 的交互响应与审批反馈
func TestTUI_PermissionApproval_InteractiveFlow(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag)
	m.messages = []ChatMessage{{Sender: "coustea", Content: ""}}
	m.isGenerating = true

	req := &protocol.PermissionRequest{
		RequestID: "tc-test",
		ToolName:  "bash",
		Arguments: `{"command":"rm -rf ./tmp"}`,
		Reason:    "potentially destructive shell command: rm -rf ./tmp",
	}

	// 1. 模拟收到来自 Agent Harness 的流式权限审批请求
	eventMsg := agentStreamEventMsg{
		event: protocol.Event{
			Type:       protocol.EventPermissionReq,
			Permission: req,
		},
		ch: make(<-chan protocol.Event),
	}

	mIntf, _ := m.Update(eventMsg)
	m = mIntf.(Model)

	if m.pendingPerm == nil {
		t.Fatalf("expected pendingPerm to be set upon EventPermissionReq")
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

	if m.pendingPerm != nil {
		t.Errorf("expected pendingPerm to be cleared after user approval")
	}

	if ag.lastPermissionReqID != "tc-test" {
		t.Errorf("expected reqID tc-test, got %s", ag.lastPermissionReqID)
	}
	if ag.lastDecision != protocol.DecisionAllowOnce {
		t.Errorf("expected DecisionAllowOnce, got %v", ag.lastDecision)
	}
}

func TestTUIFlow_Spark(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag)

	// 1. 触发 /model
	m.chatInput.SetValue("/model")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 2. 下移三次选择 Spark (第 4 项，索引 3)
	for i := 0; i < 3; i++ {
		mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
		m = mIntf.(Model)
	}

	if m.cursor != 3 {
		t.Fatalf("expected cursor to be 3 for spark, got %d", m.cursor)
	}

	// 3. 回车选中 Spark
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputAPIKey {
		t.Fatalf("expected stateInputAPIKey, got %v", m.state)
	}
	if m.currentProvider != "spark" {
		t.Fatalf("expected provider spark, got %q", m.currentProvider)
	}

	// 4. 输入 APIKey
	m.apiKeyInput.SetValue("sk-spark-test-secret")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel, got %v", m.state)
	}
	if m.currentModel != "lite" {
		t.Fatalf("expected default spark model lite, got %s", m.currentModel)
	}

	// 5. 回车确认默认模型
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected stateChat after model input, got %v", m.state)
	}
	if ag.cfgView.Provider != "spark" || ag.cfgView.ModelName != "lite" {
		t.Fatalf("agent config mismatch: %+v", ag.cfgView)
	}
}
