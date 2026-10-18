package tui

import (
	"context"
	"strings"
	"testing"
	"time"

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
	updateConfigErr     error
}

func newMockAgent(replies ...string) *mockTestAgent {
	return &mockTestAgent{
		cfgView: protocol.ConfigView{
			Provider:           "llamacpp",
			ModelName:          "local-model",
			HasAPIKey:          true,
			AvailableProviders: []string{"llamacpp", "deepseek", "gemini", "spark"},
			Providers: []protocol.ProviderInfo{
				{
					ID:                "llamacpp",
					Name:              "llama.cpp",
					IsLocal:           true,
					IsConfigured:      true,
					CurrentModel:      "local-model",
					RecommendedModels: []string{"local-model", "qwen2.5-coder-7b"},
				},
				{
					ID:                "deepseek",
					Name:              "DeepSeek",
					IsLocal:           false,
					IsConfigured:      false,
					CurrentModel:      "deepseek-flash",
					RecommendedModels: []string{"deepseek-flash", "deepseek-v4-pro", "deepseek-reasoner"},
				},
				{
					ID:                "gemini",
					Name:              "Google Gemini",
					IsLocal:           false,
					IsConfigured:      false,
					CurrentModel:      "gemini-2.5-flash",
					RecommendedModels: []string{"gemini-2.5-flash", "gemini-2.5-pro"},
				},
				{
					ID:                "spark",
					Name:              "讯飞星辰 MaaS",
					IsLocal:           false,
					IsConfigured:      false,
					CurrentModel:      "spark-2.5",
					RecommendedModels: []string{"spark-2.5", "spark-2.5-4b", "spark-x2.5", "spark-x2.5-4b", "spark-lite"},
				},
			},
		},
		replies: replies,
	}
}

func (m *mockTestAgent) Run(ctx context.Context, prompt string) (<-chan protocol.Event, error) {
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
	pStr := strings.TrimSpace(provider)
	mStr := strings.TrimSpace(model)
	if pStr == "" && mStr != "" {
		if strings.HasPrefix(mStr, "gemini") {
			pStr = "gemini"
		} else if strings.HasPrefix(mStr, "deepseek") {
			pStr = "deepseek"
		} else if strings.HasPrefix(mStr, "spark") || mStr == "lite" {
			pStr = "spark"
		} else {
			pStr = "llamacpp"
		}
	}
	if pStr != "" {
		m.cfgView.Provider = pStr
	}
	if apiKey != "" {
		m.cfgView.HasAPIKey = true
	}
	if mStr != "" {
		m.cfgView.ModelName = mStr
	}
	for i := range m.cfgView.Providers {
		p := &m.cfgView.Providers[i]
		if p.ID == m.cfgView.Provider {
			if apiKey != "" {
				p.IsConfigured = true
			}
			if mStr != "" {
				p.CurrentModel = mStr
			}
		}
	}
	return nil
}

func (m *mockTestAgent) MemoryCount() int {
	return m.memoryCount
}

func (m *mockTestAgent) WorkDir() string { return "/mock/workdir" }

func (m *mockTestAgent) Traces() []protocol.TraceEvent {
	return []protocol.TraceEvent{
		{
			Step:      -1,
			Type:      "turn_start",
			Title:     "👤 用户提问 · 模拟轮次",
			Timestamp: time.Now(),
			Payload: map[string]any{
				"turn_id": "turn_mock_123",
				"prompt":  "查看项目文件",
			},
		},
		{
			Step:      0,
			Type:      "llm_req",
			Title:     "Step 0 · 📤 LLM 请求上下文",
			Timestamp: time.Now(),
			Payload: map[string]any{
				"model": "deepseek-reasoner",
				"messages": []protocol.Message{
					{Role: protocol.RoleUser, Content: "查看项目文件"},
				},
			},
		},
	}
}

func TestTUIFlow(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag)

	// 1. 验证主线设计：初始状态必须直接是对话页面（输入框交互）
	if m.state != stateChat {
		t.Fatalf("expected initial mainline state to be stateChat, got %v", m.state)
	}

	// 2. 验证主线对话交互：发送普通消息实时在界面展示
	m.chatInput.SetValue("Hello Tide, this is mainline chat!")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if len(m.messages) == 0 {
		t.Fatalf("expected messages to have content")
	}
	lastUserMsg := m.messages[len(m.messages)-2]
	if lastUserMsg.Sender != "You" || lastUserMsg.Content != "Hello Tide, this is mainline chat!" {
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

	// 6. 验证输入 API Key 后进入模型规格点选菜单，且默认光标落在推荐模型上
	if m.state != stateSelectModelPreset {
		t.Fatalf("expected stateSelectModelPreset, got %v", m.state)
	}
	if m.currentModel != "deepseek-flash" {
		t.Fatalf("expected default deepseek-flash model, got %s", m.currentModel)
	}

	// 回车确认选定模型
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 7. 验证支线配置完成后自动无缝回到主线对话页面
	if m.state != stateChat {
		t.Fatalf("expected state to return to stateChat, got %v", m.state)
	}
	if ag.cfgView.Provider != "deepseek" || ag.cfgView.ModelName != "deepseek-flash" {
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
		Sender:  "Tide",
		Content: "Thinking...",
	})

	// 1. 模拟收到 EventToolCallStart
	mIntf, _ := m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type: protocol.EventToolCallStart,
			ToolCall: &protocol.ToolCall{
				ID:        "call_1",
				Name:      "read_file",
				Arguments: `{"path": "sample.go"}`,
			},
		},
	})
	m = mIntf.(Model)

	lastMsg := m.messages[len(m.messages)-1]
	if len(lastMsg.ToolCalls) == 0 || lastMsg.ToolCalls[0].Call.Name != "read_file" {
		t.Fatalf("expected tool call to be recorded in ToolCalls, got: %+v", lastMsg.ToolCalls)
	}

	// 2. 模拟收到 EventToolCallResult
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type: protocol.EventToolCallResult,
			ToolResult: &protocol.ToolResult{
				ToolCallID: "call_1",
				Name:       "read_file",
				Content:    "package main\nfunc main() {}",
				IsError:    false,
			},
		},
	})
	m = mIntf.(Model)

	lastMsg = m.messages[len(m.messages)-1]
	if len(lastMsg.ToolCalls) == 0 || lastMsg.ToolCalls[0].Result == nil || !strings.Contains(lastMsg.ToolCalls[0].Result.Content, "package main") {
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
	if lastMsg.Sender != "Tide" || !strings.Contains(lastMsg.Content, "Hello Alice") {
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
	if lastMsg.Sender != "Tide" || !strings.Contains(lastMsg.Content, "Your name is Alice") {
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

	if m.state != stateSelectModelPreset {
		t.Fatalf("expected stateSelectModelPreset, got %v", m.state)
	}
	if m.currentModel != "gemini-2.5-flash" {
		t.Fatalf("expected default gemini model gemini-2.5-flash, got %s", m.currentModel)
	}

	// 回车确认选择该规格并保存
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
	ag.cfgView.ModelName = "deepseek-flash"
	ag.cfgView.Providers[1].IsConfigured = true
	ag.cfgView.Providers[1].CurrentModel = "deepseek-flash"

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

	// 输入 Gemini Key 并确认规格
	m.apiKeyInput.SetValue("sk-gemini-preserved-key")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if ag.cfgView.Provider != "gemini" {
		t.Fatalf("expected switched to gemini, got %s", ag.cfgView.Provider)
	}

	// 2. 再次通过 /model 切回 DeepSeek：已配置平台支持 Enter 一键极速直切 (无需重复输入密钥与模型)
	m.chatInput.SetValue("/model")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 当前在 Gemini (索引 2)，上移一次选中已配置的 DeepSeek (索引 1)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyUp})
	m = mIntf.(Model)

	// 按下 Enter：一键极速切换直接回到对话！
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected fast-switch return to stateChat, got %v", m.state)
	}
	if ag.cfgView.Provider != "deepseek" {
		t.Fatalf("expected deepseek, got %+v", ag.cfgView)
	}
}

// 测试键盘按键操作：退出 (Ctrl+C, Ctrl+D, /exit, /quit, /q) 以及生成中断 (Ctrl+C, Esc)
func TestTUI_KeyOperations_ExitAndInterrupt(t *testing.T) {
	m := NewModel(newMockAgent())

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
	m.messages = []ChatMessage{{Sender: "Tide", Content: "Thinking"}}

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
	m.messages = []ChatMessage{{Sender: "Tide", Content: ""}}
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

	// 4. 输入 APIKey 并回车进入规格选择
	m.apiKeyInput.SetValue("sk-spark-test-secret")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateSelectModelPreset {
		t.Fatalf("expected stateSelectModelPreset, got %v", m.state)
	}

	// 5. 下移一次选择 spark-2.5-4b 规格 (预设项第二条)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)

	// 回车确认选择 spark-2.5-4b
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected stateChat after model preset selection, got %v", m.state)
	}
	if ag.cfgView.Provider != "spark" || ag.cfgView.ModelName != "spark-2.5-4b" {
		t.Fatalf("agent config mismatch: %+v", ag.cfgView)
	}
}

// 测试聊天框直接输入 /model <args> 快捷切换指令
func TestTUI_ChatInlineModelSwitching(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag)

	// 1. 输入 /model gemini (未配置 Key 时直接拉起 API Key 输入向导)
	m.chatInput.SetValue("/model gemini")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputAPIKey {
		t.Fatalf("expected stateInputAPIKey for unconfigured gemini, got %v", m.state)
	}
	if m.currentProvider != "gemini" {
		t.Fatalf("expected provider gemini, got %s", m.currentProvider)
	}

	// 2. 先将 gemini 标记为已就绪
	ag.cfgView.Providers[2].IsConfigured = true
	m.state = stateChat

	// 3. 对话框输入 /model gemini 极速静默切换
	m.chatInput.SetValue("/model gemini")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected stateChat on inline fast-switch, got %v", m.state)
	}
	if ag.cfgView.Provider != "gemini" {
		t.Fatalf("expected switched to gemini, got %s", ag.cfgView.Provider)
	}

	// 4. 对话框输入具体模型名称 /model deepseek-reasoner 智能推断厂商并切换
	m.chatInput.SetValue("/model deepseek-reasoner")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected stateChat on inline model switch, got %v", m.state)
	}
	if ag.cfgView.Provider != "deepseek" || ag.cfgView.ModelName != "deepseek-reasoner" {
		t.Fatalf("expected deepseek and deepseek-reasoner, got: %+v", ag.cfgView)
	}
}

// 测试通过 'm' 键选择预设模型规格与自定义模型输入
func TestTUI_PresetModelSpecsMenu(t *testing.T) {
	ag := newMockAgent()
	ag.cfgView.Providers[1].IsConfigured = true // DeepSeek 已就绪
	m := NewModel(ag)

	// 1. 呼出看板
	m.chatInput.SetValue("/model")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 光标移至 DeepSeek
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)

	// 2. 按 'm' 展开模型规格列表
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'m'}})
	m = mIntf.(Model)

	if m.state != stateSelectModelPreset {
		t.Fatalf("expected stateSelectModelPreset after pressing 'm', got %v", m.state)
	}

	// 3. 下移一次选择 deepseek-v4-pro 并回车
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat, got %v", m.state)
	}
	if ag.cfgView.Provider != "deepseek" || ag.cfgView.ModelName != "deepseek-v4-pro" {
		t.Fatalf("expected deepseek-v4-pro, got %+v", ag.cfgView)
	}

	// 4. 测试自定义输入模型名称
	m.chatInput.SetValue("/model")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)

	// 按 'm' 展开
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'m'}})
	m = mIntf.(Model)

	// 移至最后一项: [+] 自定义输入模型名称...
	for i := 0; i < len(m.presetChoices)-1; i++ {
		mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
		m = mIntf.(Model)
	}

	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel on custom choice, got %v", m.state)
	}

	m.modelInput.SetValue("my-custom-deepseek-v4")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat, got %v", m.state)
	}
	if ag.cfgView.ModelName != "my-custom-deepseek-v4" {
		t.Fatalf("expected my-custom-deepseek-v4, got %s", ag.cfgView.ModelName)
	}
}

// 测试顶栏目录展示取自 Agent 契约 (WorkDir)，而非进程自身 cwd
func TestTUI_HeaderUsesAgentWorkDir(t *testing.T) {
	m := NewModel(newMockAgent())
	view := ansi.Strip(m.View())
	if !strings.Contains(view, "目录: /mock/workdir") {
		t.Fatalf("expected header to show agent workdir, got:\n%s", view)
	}
}

// 测试未就绪内核（远程厂商缺密钥）的欢迎语与发送引导
func TestTUI_UnreadyAgent_GuidesToConfiguration(t *testing.T) {
	ag := newMockAgent()
	ag.cfgView.Provider = "deepseek"
	ag.cfgView.ModelName = "deepseek-flash"
	ag.cfgView.HasAPIKey = false
	m := NewModel(ag)

	// 1. 欢迎语提示尚未配置密钥
	welcomeShown := false
	for _, msg := range m.messages {
		if strings.Contains(msg.Content, "尚未配置 API Key") {
			welcomeShown = true
			break
		}
	}
	if !welcomeShown {
		t.Fatalf("expected welcome message to mention missing API key, got: %+v", m.messages)
	}

	// 2. 直接发送消息应被引导至 /model 向导，而不是发起流式请求
	m.chatInput.SetValue("你好")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	last := m.messages[len(m.messages)-1]
	if !strings.Contains(last.Content, "未配置可用模型") {
		t.Fatalf("expected send to be blocked with configuration guidance, got: %+v", last)
	}
	if m.isGenerating {
		t.Fatalf("expected generation to stay idle for unready agent")
	}
}

func TestTUI_TraceInspector_Flow(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag)
	m.width = 100
	m.height = 30

	// 1. 输入 /log 进入追踪审计看板
	m.chatInput.SetValue("/log")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateTraceInspector {
		t.Fatalf("expected stateTraceInspector after /log, got %v", m.state)
	}

	// 2. 验证渲染视图包含看板标题与 JSON 关键字段
	view := m.View()
	if !strings.Contains(view, "全系统执行链路与详细 JSON 追踪看板") {
		t.Errorf("expected view to contain trace inspector header, got:\n%s", view)
	}
	if !strings.Contains(view, "turn_mock_123") {
		t.Errorf("expected view to contain first event's JSON text, got:\n%s", view)
	}

	// 3. 向下移动光标至下一个事件 (Step 0)
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown})
	m = mIntf.(Model)
	if m.traceCursor != 1 {
		t.Errorf("expected traceCursor to be 1, got %d", m.traceCursor)
	}
	view = m.View()
	if !strings.Contains(view, "deepseek-reasoner") {
		t.Errorf("expected view to update to second event JSON, got:\n%s", view)
	}

	// 4. 按 Tab 切换焦点到右侧 JSON 视口
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyTab})
	m = mIntf.(Model)
	if !m.traceFocusRight {
		t.Errorf("expected traceFocusRight to be true after Tab")
	}

	// 5. 按 Esc 返回主对话页面
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	m = mIntf.(Model)
	if m.state != stateChat {
		t.Fatalf("expected stateChat after Esc, got %v", m.state)
	}

	// 6. 测试 Ctrl+L 快捷键一键唤出看板
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyCtrlL})
	m = mIntf.(Model)
	if m.state != stateTraceInspector {
		t.Fatalf("expected stateTraceInspector after Ctrl+L, got %v", m.state)
	}

	// 7. 在看板中按 q 返回
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})
	m = mIntf.(Model)
	if m.state != stateChat {
		t.Fatalf("expected stateChat after q, got %v", m.state)
	}
}
