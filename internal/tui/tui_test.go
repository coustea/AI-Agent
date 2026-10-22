package tui

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	"my-agent/internal/protocol"
	"my-agent/pkg/llm"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
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
			BaseURL:   "http://127.0.0.1:11434/v1",
			ModelName: "local-model",
			HasAPIKey: true,
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
		ch <- protocol.Event{Type: protocol.EventDone, Usage: &llm.Usage{TotalTokens: 20}}
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

func (m *mockTestAgent) UpdateConfig(baseURL, apiKey, model string) error {
	if m.updateConfigErr != nil {
		return m.updateConfigErr
	}
	bStr := strings.TrimSpace(baseURL)
	mStr := strings.TrimSpace(model)
	if bStr != "" {
		m.cfgView.BaseURL = bStr
	}
	if apiKey != "" {
		m.cfgView.HasAPIKey = true
	}
	if mStr != "" {
		m.cfgView.ModelName = mStr
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
				"messages": []llm.Message{
					{Role: llm.RoleUser, Content: "查看项目文件"},
				},
			},
		},
	}
}

func TestTUIFlow(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)

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

	// 3. 验证向导触发：在输入框输入 /model 调出三要素配置向导
	m.chatInput.SetValue("/model")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 步骤 1: BaseURL 输入
	if m.state != stateInputBaseURL {
		t.Fatalf("expected state to switch to stateInputBaseURL after /model, got %v", m.state)
	}

	m.baseURLInput.SetValue("https://api.deepseek.com/v1")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 步骤 2: API Key 输入
	if m.state != stateInputAPIKey {
		t.Fatalf("expected stateInputAPIKey, got %v", m.state)
	}
	if m.wizardBaseURL != "https://api.deepseek.com/v1" {
		t.Fatalf("expected wizardBaseURL https://api.deepseek.com/v1, got %q", m.wizardBaseURL)
	}

	m.apiKeyInput.SetValue("sk-test-key-123456")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 步骤 3: Model 模型名称输入
	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel, got %v", m.state)
	}

	m.modelInput.SetValue("deepseek-chat")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 4. 验证向导配置完成后自动无缝回到主线对话页面
	if m.state != stateChat {
		t.Fatalf("expected state to return to stateChat, got %v", m.state)
	}
	if ag.cfgView.BaseURL != "https://api.deepseek.com/v1" || ag.cfgView.ModelName != "deepseek-chat" {
		t.Fatalf("agent config mismatch: %+v", ag.cfgView)
	}

	// 5. 验证 View 渲染正常
	viewOutput := m.View()
	if viewOutput == "" {
		t.Fatalf("expected non-empty view output")
	}
}

func TestTUIToolEventRendering(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)
	m.messages = append(m.messages, ChatMessage{
		Sender:  "Tide",
		Content: "Thinking...",
	})

	// 1. 模拟收到 EventToolCallStart
	mIntf, _ := m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type: protocol.EventToolCallStart,
			ToolCall: &llm.ToolCall{
				ID:        "call_1",
				Name:      "read_file",
				Arguments: `{"path": "sample.go"}`,
			},
		},
	})
	m = mIntf.(Model)

	lastMsg := m.messages[len(m.messages)-1]
	var tcRec *ToolCallRecord
	for _, b := range lastMsg.Blocks {
		if b.Kind == BlockTool && b.Tool != nil {
			tcRec = b.Tool
			break
		}
	}
	if tcRec == nil || tcRec.Call.Name != "read_file" {
		t.Fatalf("expected tool call to be recorded in blocks, got: %+v", lastMsg.Blocks)
	}

	// 2. 模拟收到 EventToolCallResult
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type: protocol.EventToolCallResult,
			ToolResult: &llm.ToolResult{
				ToolCallID: "call_1",
				Name:       "read_file",
				Content:    "package main\nfunc main() {}",
				IsError:    false,
			},
		},
	})
	m = mIntf.(Model)

	lastMsg = m.messages[len(m.messages)-1]
	tcRec = nil
	for _, b := range lastMsg.Blocks {
		if b.Kind == BlockTool && b.Tool != nil {
			tcRec = b.Tool
			break
		}
	}
	if tcRec == nil || tcRec.Result == nil || !strings.Contains(tcRec.Result.Content, "package main") {
		t.Fatalf("expected tool result to be recorded in blocks, got: %+v", lastMsg.Blocks)
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

func TestTUI_SequentialBlocksRendering(t *testing.T) {
	ag := newMockAgent("mock")
	m := NewModel(ag, ag)

	// 初始一条 Tide 正在生成的消息
	m.messages = append(m.messages, ChatMessage{
		Sender: "Tide",
	})

	// 1. 模拟收到思考事件
	mIntf, _ := m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type:      protocol.EventReasoningDelta,
			Reasoning: "AlphaThinking",
		},
	})
	m = mIntf.(Model)

	// 2. 模拟调用工具前输出的引导说明文字
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type:  protocol.EventDelta,
			Delta: "BetaPreToolText",
		},
	})
	m = mIntf.(Model)

	// 3. 模拟工具调用开始
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type: protocol.EventToolCallStart,
			ToolCall: &llm.ToolCall{
				ID:        "c_1",
				Name:      "GammaToolBash",
				Arguments: `{"command": "ls"}`,
			},
		},
	})
	m = mIntf.(Model)

	// 4. 模拟工具调用结束
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type: protocol.EventToolCallResult,
			ToolResult: &llm.ToolResult{
				ToolCallID: "c_1",
				Name:       "GammaToolBash",
				Content:    "DeltaToolResultFiles",
			},
		},
	})
	m = mIntf.(Model)

	// 5. 模拟工具返回后，模型继续输出的最终总结说明
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type:  protocol.EventDelta,
			Delta: "EpsilonPostToolText",
		},
	})
	m = mIntf.(Model)

	rendered := m.renderChatMessages()

	idx1 := strings.Index(rendered, "AlphaThinking")
	idx2 := strings.Index(rendered, "BetaPreToolText")
	idx3 := strings.Index(rendered, "GammaToolBash")
	idx4 := strings.Index(rendered, "DeltaToolResultFiles")
	idx5 := strings.Index(rendered, "EpsilonPostToolText")

	if idx1 == -1 || idx2 == -1 || idx3 == -1 || idx4 == -1 || idx5 == -1 {
		t.Fatalf("expected all steps to be present in rendered content, got: %s", rendered)
	}

	// 严格断言位置必须是按时间发生顺序递增，绝不能发生插入或乱序颠倒
	if !(idx1 < idx2 && idx2 < idx3 && idx3 < idx4 && idx4 < idx5) {
		t.Fatalf("expected strictly sequential rendering (idx1 < idx2 < idx3 < idx4 < idx5), but got: %d, %d, %d, %d, %d",
			idx1, idx2, idx3, idx4, idx5)
	}
}

func TestTUI_EndToEnd_MultiTurn_Chat(t *testing.T) {
	ag := newMockAgent(
		"Hello Alice! Nice to meet you.",
		"Your name is Alice.",
	)
	m := NewModel(ag, ag)

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

	// 验证两轮对话消息渲染内容 (去除 ANSI 控制码后验证语义内容)
	strippedChat := ansi.Strip(m.renderChatMessages())
	if !strings.Contains(strippedChat, "My name is Alice") || !strings.Contains(strippedChat, "Your name is Alice") {
		t.Errorf("messages missing expected conversation content:\n%s", strippedChat)
	}
}

func TestTUIFlow_FastSwitchModel(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)

	// 快速切模 /model gemini-2.5-flash
	m.chatInput.SetValue("/model gemini-2.5-flash")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected stateChat, got %v", m.state)
	}
	if ag.cfgView.ModelName != "gemini-2.5-flash" {
		t.Fatalf("expected model to switch to gemini-2.5-flash, got %s", ag.cfgView.ModelName)
	}
}

// 测试模型切换流程
func TestTUIFlow_SwitchWithoutReenteringAPIKey(t *testing.T) {
	ag := newMockAgent()
	ag.cfgView.BaseURL = "https://api.deepseek.com/v1"
	ag.cfgView.ModelName = "deepseek-chat"
	ag.cfgView.HasAPIKey = true

	m := NewModel(ag, ag)

	// 1. 打开向导 /model
	m.chatInput.SetValue("/model")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputBaseURL {
		t.Fatalf("expected stateInputBaseURL, got %v", m.state)
	}

	// 步骤 1: 直接回车沿用 BaseURL
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 步骤 2: 直接回车沿用 API Key
	if m.state != stateInputAPIKey {
		t.Fatalf("expected stateInputAPIKey, got %v", m.state)
	}
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 步骤 3: 输入新模型名称
	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel, got %v", m.state)
	}
	m.modelInput.SetValue("deepseek-reasoner")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat, got %v", m.state)
	}
	if ag.cfgView.ModelName != "deepseek-reasoner" {
		t.Fatalf("expected deepseek-reasoner, got %+v", ag.cfgView)
	}
	if !ag.cfgView.HasAPIKey {
		t.Fatalf("expected apiKey preserved")
	}
}

// 测试键盘按键操作：退出 (Ctrl+C, Ctrl+D, /exit, /quit, /q) 以及生成中断 (Ctrl+C, Esc)
func TestTUI_KeyOperations_ExitAndInterrupt(t *testing.T) {
	m := NewModel(newMockAgent(), nil)

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
	m.state = stateInputBaseURL
	_, cmd = m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	if cmd == nil {
		t.Fatalf("expected tea.Quit on Ctrl+C in stateInputBaseURL, got nil")
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
	m := NewModel(ag, ag)
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

	// 4. 验证权限审批完成后，审计卡片已沉淀到消息历史的 Blocks 中
	lastMsg := m.messages[len(m.messages)-1]
	if len(lastMsg.Blocks) == 0 {
		t.Fatalf("expected permission block to be appended to message blocks")
	}
	lastBlock := lastMsg.Blocks[len(lastMsg.Blocks)-1]
	if lastBlock.Kind != BlockPermission || lastBlock.Permission == nil {
		t.Fatalf("expected last block to be BlockPermission, got: %+v", lastBlock)
	}
	if lastBlock.Permission.Decision != protocol.DecisionAllowOnce {
		t.Fatalf("expected recorded decision DecisionAllowOnce, got: %v", lastBlock.Permission.Decision)
	}

	renderedChat := m.renderChatMessages()
	if !strings.Contains(renderedChat, "Gate 3 审计存根") {
		t.Errorf("expected rendered chat to contain audit card title, got:\n%s", renderedChat)
	}
	if !strings.Contains(renderedChat, "允许本次执行 (单次放行)") {
		t.Errorf("expected rendered chat to contain decision details, got:\n%s", renderedChat)
	}
}

func TestTUIFlow_LocalEndpoint(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)

	// 1. 触发 /model
	m.chatInput.SetValue("/model")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 2. 步骤 1: 设置本地 BaseURL
	m.baseURLInput.SetValue("http://127.0.0.1:11434/v1")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputAPIKey {
		t.Fatalf("expected stateInputAPIKey, got %v", m.state)
	}

	// 3. 步骤 2: 本地端点直接 Enter 跳过 API Key
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputModel {
		t.Fatalf("expected stateInputModel, got %v", m.state)
	}

	// 4. 步骤 3: 设置模型名称
	m.modelInput.SetValue("qwen2.5-coder:7b")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat, got %v", m.state)
	}
	if ag.cfgView.BaseURL != "http://127.0.0.1:11434/v1" || ag.cfgView.ModelName != "qwen2.5-coder:7b" {
		t.Fatalf("agent config mismatch: %+v", ag.cfgView)
	}
}

// 测试聊天框直接输入 /model <args> 快捷切换指令
func TestTUI_ChatInlineModelSwitching(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)

	// 1. 对话框输入具体模型名称 /model deepseek-reasoner
	m.chatInput.SetValue("/model deepseek-reasoner")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected stateChat on inline model switch, got %v", m.state)
	}
	if ag.cfgView.ModelName != "deepseek-reasoner" {
		t.Fatalf("expected deepseek-reasoner, got: %+v", ag.cfgView)
	}

	// 2. 再次快捷切换为 gpt-4o
	m.chatInput.SetValue("/model gpt-4o")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if ag.cfgView.ModelName != "gpt-4o" {
		t.Fatalf("expected gpt-4o, got: %+v", ag.cfgView)
	}
}

// 测试向导取消返回对话流程
func TestTUI_WizardCancelFlow(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)

	// 1. 呼出向导
	m.chatInput.SetValue("/model")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateInputBaseURL {
		t.Fatalf("expected stateInputBaseURL, got %v", m.state)
	}

	// 2. 按 Esc 取消
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat after Esc, got %v", m.state)
	}
}

// 测试顶栏目录展示取自 Agent 契约 (WorkDir)，而非进程自身 cwd
func TestTUI_HeaderUsesAgentWorkDir(t *testing.T) {
	m := NewModel(newMockAgent(), nil)
	view := ansi.Strip(m.View())
	if !strings.Contains(view, "/mock/workdir") {
		t.Fatalf("expected header to show agent workdir, got:\n%s", view)
	}
}

// 测试未就绪内核（缺密钥）的欢迎语与发送引导
func TestTUI_UnreadyAgent_GuidesToConfiguration(t *testing.T) {
	ag := newMockAgent()
	ag.cfgView.BaseURL = "https://api.deepseek.com/v1"
	ag.cfgView.ModelName = "deepseek-flash"
	ag.cfgView.HasAPIKey = false
	m := NewModel(ag, ag)

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
	m := NewModel(ag, ag)
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
	if !strings.Contains(view, "全系统执行链路与底层 JSON 追踪看板") {
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

	// 4. 按 Tab 切换焦点到下方全宽 JSON 视口
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyTab})
	m = mIntf.(Model)
	if !m.traceFocusJSON {
		t.Errorf("expected traceFocusJSON to be true after Tab")
	}

	// 测试按 'r' 键在 Clean JSON 与 Raw JSON 之间自由切换
	if m.traceRawMode {
		t.Errorf("expected default traceRawMode to be false")
	}
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	m = mIntf.(Model)
	if !m.traceRawMode {
		t.Errorf("expected traceRawMode to be true after pressing r")
	}
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	m = mIntf.(Model)
	if m.traceRawMode {
		t.Errorf("expected traceRawMode to toggle back to false after pressing r again")
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

func TestLipglossBoxModelWidth(t *testing.T) {
	cardW := 80
	// 外层: Width(80), Border(2), Padding(0, 1)(2)
	// 内层期望总宽: 80 - 2 = 78
	// 内层带 Border(2)，所以内层 Width 应为 78 - 2 = 76
	inner := lipgloss.NewStyle().
		Width(76).
		Border(lipgloss.RoundedBorder()).
		Padding(0, 1).
		Render("inner content")
	if lipgloss.Width(inner) != 78 {
		t.Fatalf("expected inner width 78, got %d", lipgloss.Width(inner))
	}

	outer := lipgloss.NewStyle().
		Width(cardW).
		Border(lipgloss.RoundedBorder()).
		Padding(0, 1).
		Render(inner)
	if lipgloss.Width(outer) != 82 { // 80 + 2
		t.Fatalf("expected outer width 82, got %d", lipgloss.Width(outer))
	}
}

func TestTUI_ToolAndPermissionCardRendering(t *testing.T) {
	// 1. 测试工具执行中卡片
	runningCard := renderToolCard(ToolCallRecord{
		Call: llm.ToolCall{
			ID:        "c_run",
			Name:      "bash",
			Arguments: `{"command": "sleep 1"}`,
		},
		Result: nil,
	}, 80)
	if !strings.Contains(runningCard, "RUNNING") || !strings.Contains(runningCard, "bash") || !strings.Contains(runningCard, "sleep 1") {
		t.Errorf("unexpected running tool card: %s", runningCard)
	}

	// 2. 测试工具成功卡片
	successCard := renderToolCard(ToolCallRecord{
		Call: llm.ToolCall{
			ID:        "c_succ",
			Name:      "read_file",
			Arguments: `{"path": "main.go"}`,
		},
		Result: &llm.ToolResult{
			ToolCallID: "c_succ",
			Name:       "read_file",
			Content:    "package main\n\nfunc main() {}",
			IsError:    false,
		},
	}, 80)
	if !strings.Contains(successCard, "SUCCESS") || !strings.Contains(successCard, "read_file") || !strings.Contains(successCard, "package main") {
		t.Errorf("unexpected success tool card: %s", successCard)
	}

	// 3. 测试工具报错卡片
	errorCard := renderToolCard(ToolCallRecord{
		Call: llm.ToolCall{
			ID:        "c_err",
			Name:      "bash",
			Arguments: `{"command": "exit 1"}`,
		},
		Result: &llm.ToolResult{
			ToolCallID: "c_err",
			Name:       "bash",
			Content:    "exit status 1: command not found",
			IsError:    true,
		},
	}, 80)
	if !strings.Contains(errorCard, "ERROR") || !strings.Contains(errorCard, "bash") || !strings.Contains(errorCard, "exit status 1") {
		t.Errorf("unexpected error tool card: %s", errorCard)
	}

	// 4. 测试权限审计卡片 (三种决策)
	permReq := protocol.PermissionRequest{
		ToolName:  "bash",
		Arguments: `{"command": "rm -rf ."}`,
		Reason:    "destructive rm",
	}

	onceCard := renderPermissionAuditCard(PermissionRecord{
		Request:  permReq,
		Decision: protocol.DecisionAllowOnce,
	}, 80)
	if !strings.Contains(onceCard, "Gate 3 审计存根") || !strings.Contains(onceCard, "允许本次执行 (单次放行)") {
		t.Errorf("unexpected once audit card: %s", onceCard)
	}

	sessionCard := renderPermissionAuditCard(PermissionRecord{
		Request:  permReq,
		Decision: protocol.DecisionAllowSession,
	}, 80)
	if !strings.Contains(sessionCard, "本会话始终信任同类命令") {
		t.Errorf("unexpected session audit card: %s", sessionCard)
	}

	denyCard := renderPermissionAuditCard(PermissionRecord{
		Request:  permReq,
		Decision: protocol.DecisionDeny,
	}, 80)
	if !strings.Contains(denyCard, "拒绝执行并安全阻断") {
		t.Errorf("unexpected deny audit card: %s", denyCard)
	}
}

func TestTUI_ThinkingViewer_Flow(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)
	m.width = 100
	m.height = 30

	// 1. 无思考记录时打开看空提示
	m.chatInput.SetValue("/think")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if m.state != stateThinkingViewer {
		t.Fatalf("expected stateThinkingViewer after /think, got %v", m.state)
	}

	viewEmpty := m.View()
	if !strings.Contains(viewEmpty, "当前会话暂无思考过程记录") {
		t.Errorf("expected view to contain empty notice, got:\n%s", viewEmpty)
	}

	// 按 q 退出返回对话
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})
	m = mIntf.(Model)
	if m.state != stateChat {
		t.Fatalf("expected stateChat after q, got %v", m.state)
	}

	// 2. 构造包含两轮对话思考记录的数据
	m.messages = []ChatMessage{
		{
			Sender:  "You",
			Content: "提问一：如何设计网关？",
		},
		{
			Sender: "Tide",
			Blocks: []MessageBlock{
				{
					Kind: BlockReasoning,
					Text: "思考网关架构：首先需要支持多厂商，其次需要统一协议与动态路由。",
				},
				{
					Kind: BlockText,
					Text: "网关设计方案如下...",
				},
			},
		},
		{
			Sender:  "You",
			Content: "提问二：如何设计权限？",
		},
		{
			Sender: "Tide",
			Blocks: []MessageBlock{
				{
					Kind: BlockReasoning,
					Text: "思考权限体系：采用三道闸门设计，Gate 1 硬拒绝，Gate 2 规则匹配，Gate 3 交互审批。",
				},
				{
					Kind: BlockText,
					Text: "权限设计方案如下...",
				},
			},
		},
	}

	// 3. 测试通过 Ctrl+T 快捷键打开思考看板
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyCtrlT})
	m = mIntf.(Model)
	if m.state != stateThinkingViewer {
		t.Fatalf("expected stateThinkingViewer after Ctrl+T, got %v", m.state)
	}
	if len(m.thinkingEntries) != 2 {
		t.Fatalf("expected 2 thinking entries, got %d", len(m.thinkingEntries))
	}
	// 默认光标定位在最新的思考过程 (第 2 项，索引 1)
	if m.thinkingCursor != 1 {
		t.Fatalf("expected thinkingCursor to be 1, got %d", m.thinkingCursor)
	}

	view := m.View()
	if !strings.Contains(view, "三道闸门设计") {
		t.Errorf("expected view to contain latest thinking text, got:\n%s", view)
	}

	// 4. 按左键切换至第一项思考过程
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyLeft})
	m = mIntf.(Model)
	if m.thinkingCursor != 0 {
		t.Fatalf("expected thinkingCursor to be 0, got %d", m.thinkingCursor)
	}
	view = m.View()
	if !strings.Contains(view, "思考网关架构") {
		t.Errorf("expected view to contain first thinking text, got:\n%s", view)
	}

	// 5. 按 Tab 循环切回第二项
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyTab})
	m = mIntf.(Model)
	if m.thinkingCursor != 1 {
		t.Fatalf("expected thinkingCursor to be 1 after Tab, got %d", m.thinkingCursor)
	}

	// 6. 按 'r' 键切换 Raw 模式
	if m.thinkingRawMode {
		t.Fatalf("expected thinkingRawMode initially false")
	}
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	m = mIntf.(Model)
	if !m.thinkingRawMode {
		t.Fatalf("expected thinkingRawMode true after r")
	}

	// 7. 测试在思考看板打开期间，流式增量实时同步更新
	m.isGenerating = true
	mIntf, _ = m.Update(agentStreamEventMsg{
		event: protocol.Event{
			Type:      protocol.EventReasoningDelta,
			Reasoning: "【实时增量推理中...】",
		},
	})
	m = mIntf.(Model)

	viewUpdated := m.View()
	if !strings.Contains(viewUpdated, "【实时增量推理中...】") {
		t.Errorf("expected real-time streaming reasoning update in view, got:\n%s", viewUpdated)
	}

	// 8. 再次按 Ctrl+T 返回对话页面
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyCtrlT})
	m = mIntf.(Model)
	if m.state != stateChat {
		t.Fatalf("expected stateChat after toggling Ctrl+T, got %v", m.state)
	}
}

// 验收 D8：块级渲染缓存命中与宽度隔离
func TestRenderMarkdownCache_HitAndWidthIsolation(t *testing.T) {
	mdCacheMu.Lock()
	mdCache = make(map[uint64]string)
	mdCacheMu.Unlock()

	out1 := renderMarkdownCached("**bold** and `code`", 80)
	if len(mdCache) != 1 {
		t.Fatalf("expected 1 cache entry, got %d", len(mdCache))
	}

	out2 := renderMarkdownCached("**bold** and `code`", 80)
	if out1 != out2 {
		t.Errorf("cached render must be stable")
	}
	if len(mdCache) != 1 {
		t.Errorf("cache hit must not add entries, got %d", len(mdCache))
	}

	_ = renderMarkdownCached("**bold** and `code`", 60)
	if len(mdCache) != 2 {
		t.Errorf("different width must produce a separate cache entry, got %d", len(mdCache))
	}
}

// 验收 D12：向导取消后暂存的 API Key 与 BaseURL 不得残留
func TestTUI_WizardStateCleanedOnCancel(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)

	// 1. 打开 /model，输入 BaseURL 与 Key
	m.chatInput.SetValue("/model")
	mIntf, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	m.baseURLInput.SetValue("https://api.test.com/v1")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	m.apiKeyInput.SetValue("sk-test-secret")
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	// 2. 在模型输入步骤按 Esc 取消向导
	mIntf, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	m = mIntf.(Model)

	if m.state != stateChat {
		t.Fatalf("expected return to stateChat on Esc, got %v", m.state)
	}
	if m.wizardBaseURL != "" || m.wizardAPIKey != "" {
		t.Fatalf("wizard temporary state leaked after cancel: url=%q, key=%q",
			m.wizardBaseURL, m.wizardAPIKey)
	}
}

// 验收 D9：shutdown 必须取消运行中轮次并清除挂起审批态
func TestTUI_ShutdownClearsPendingPermission(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)

	cancelled := false
	m.cancel = func() { cancelled = true }
	m.isGenerating = true
	m.pendingPerm = &protocol.PermissionRequest{RequestID: "perm_1", ToolName: "bash"}

	m.shutdown()

	if !cancelled {
		t.Errorf("shutdown must cancel the running turn")
	}
	if m.cancel != nil {
		t.Errorf("cancel must be released after shutdown")
	}
	if m.pendingPerm != nil {
		t.Errorf("pending permission must be cleared on shutdown")
	}
	if m.isGenerating {
		t.Errorf("isGenerating must be reset on shutdown")
	}
}

func TestTUI_ViewLayoutHeight(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)
	for i := 0; i < 20; i++ {
		m.messages = append(m.messages, ChatMessage{
			Sender:  "You",
			Content: fmt.Sprintf("Question %d with some longer text to fill up lines in viewport", i),
		})
		m.messages = append(m.messages, ChatMessage{
			Sender:  "Tide",
			Content: fmt.Sprintf("Answer %d with multiple lines of helpful responses from assistant\nLine 2 of answer\nLine 3 of answer", i),
		})
	}
	mIntf, _ := m.Update(tea.WindowSizeMsg{Width: 80, Height: 24})
	m = mIntf.(Model)
	out := m.View()
	h := lipgloss.Height(out)
	t.Logf("Height of View with many messages in 24-line terminal: %d", h)
	if h > 24 {
		t.Errorf("View height %d exceeds window height 24", h)
	}

	// 验证按键不会破坏视口或使输入框异常
	for _, key := range []tea.KeyType{tea.KeyUp, tea.KeyDown, tea.KeyPgUp, tea.KeyPgDown} {
		mIntf, _ = m.Update(tea.KeyMsg{Type: key})
		m = mIntf.(Model)
		newH := lipgloss.Height(m.View())
		if newH > 24 {
			t.Errorf("View height %d exceeds window height 24 after key %v", newH, key)
		}
		if !strings.Contains(m.View(), "PROMPT · 对话模式") {
			t.Errorf("Input box disappeared after key %v", key)
		}
	}
}

func TestTUI_SlashCommand_Update(t *testing.T) {
	ag := newMockAgent()
	m := NewModel(ag, ag)
	m.chatInput.SetValue("/update")
	mIntf, cmd := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = mIntf.(Model)

	if cmd != nil {
		t.Errorf("expected nil cmd for /update, got %v", cmd)
	}
	if len(m.messages) == 0 {
		t.Fatalf("expected message appended for /update command")
	}
	lastMsg := m.messages[len(m.messages)-1]
	if !strings.Contains(lastMsg.Content, "tide update") {
		t.Errorf("expected /update response to mention 'tide update', got: %s", lastMsg.Content)
	}
}
