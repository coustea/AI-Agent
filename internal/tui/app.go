package tui

import (
	"context"
	"fmt"
	"strings"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/gateway"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// sessionState 界面状态枚举
type sessionState int

const (
	stateSelectModel sessionState = iota // 状态 1: 模型选择（官网示例风格）
	stateInputAPIKey                     // 状态 2: 输入 API Key
	stateInputModel                      // 状态 3: 输入/确认具体模型名称并保存
	stateChat                            // 状态 4: 主聊天页面（在 chat.go 中处理）
)

// agentStreamEventMsg 封装来自 Agent 的单次流式事件
type agentStreamEventMsg struct {
	event agent.AgentEvent
	ch    <-chan agent.AgentEvent
}

func waitForAgentEvent(ch <-chan agent.AgentEvent) tea.Cmd {
	return func() tea.Msg {
		event, ok := <-ch
		if !ok {
			return agentStreamEventMsg{
				event: agent.AgentEvent{Done: true},
			}
		}
		return agentStreamEventMsg{
			event: event,
			ch:    ch,
		}
	}
}

// Model 定义终端界面的整体数据状态
type Model struct {
	state sessionState

	// 配置文件与模型配置
	cfgPath string
	config  config.Config

	// 状态 1: 模型选择（官网示例风格，在 model.go 中处理）
	cursor   int
	choices  []string
	selected int

	// 状态 2 & 3: 配置输入框（在 model.go 中处理）
	apiKeyInput textinput.Model
	modelInput  textinput.Model

	// 状态 4: 聊天输入框与消息列表（在 chat.go 中处理）
	chatInput    textinput.Model
	messages     []ChatMessage
	isGenerating bool               // 是否正在流式生成中
	cancel       context.CancelFunc // 当前流式会话的中断回调

	// 权限门禁待审批请求（基于 Harness Gate 3 交互）
	pendingPrompt *agent.PermissionPrompt

	// 视口与动态指示器
	viewport       viewport.Model
	viewportReady  bool
	spinner        spinner.Model
	activeToolName string

	// 终端宽高适配
	width  int
	height int

	// 预留给后期接入 Agent 内核的契约接口
	bridge AgentBridge
}

// NewModel 初始化并返回主 Model
func NewModel(bridge AgentBridge) Model {
	cfgPath := config.DefaultConfigPath()
	existingCfg, err := config.LoadConfig(cfgPath)

	// 1. API Key 输入框
	apiKeyInput := textinput.New()
	apiKeyInput.Placeholder = "在此粘贴或输入你的 API Key (按 Enter 确认)"
	apiKeyInput.EchoMode = textinput.EchoPassword
	apiKeyInput.EchoCharacter = '•'
	apiKeyInput.CharLimit = 200
	apiKeyInput.Width = 60

	// 2. 模型名称输入框
	modelInput := textinput.New()
	modelInput.Placeholder = "输入模型名称 (如 gemini-2.5-flash / deepseek-flash)"
	modelInput.CharLimit = 100
	modelInput.Width = 60

	// 3. 聊天输入框 (Claude Code 风格)
	chatInput := textinput.New()
	chatInput.Prompt = promptPrefixStyle.Render("❯ ")
	chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
	chatInput.CharLimit = 2000
	chatInput.Width = 70

	// 4. 微动态加载指示器 (Spinner)
	sp := spinner.New()
	sp.Spinner = spinner.Dot
	sp.Style = lipgloss.NewStyle().Foreground(colorYellow)

	// 5. 消息滚动视口 (Viewport)
	vp := viewport.New(80, 20)

	m := Model{
		cfgPath: cfgPath,
		choices: []string{
			string(config.ProviderLlamaCpp),
			string(config.ProviderDeepSeek),
			string(config.ProviderGemini),
		},
		selected:    0,
		apiKeyInput: apiKeyInput,
		modelInput:  modelInput,
		chatInput:   chatInput,
		messages:    []ChatMessage{},
		bridge:      bridge,
		spinner:     sp,
		viewport:    vp,
	}

	// 主线永远是聊天对话页面（输入框交互）
	m.state = stateChat
	m.chatInput.Focus()

	// 检查是否有现有配置或可用环境配置
	if err == nil && existingCfg != nil && (existingCfg.APIKey != "" || config.IsLocalProvider(existingCfg.Provider)) {
		m.config = *existingCfg
		for i, c := range m.choices {
			if strings.EqualFold(c, string(m.config.Provider)) {
				m.selected = i
				m.cursor = i
				break
			}
		}
		if m.bridge == nil {
			if gw, gwErr := gateway.NewGatewayFromConfig(existingCfg); gwErr == nil {
				if ag, agErr := agent.NewAgent(gw, agent.WithDefaultTools()); agErr == nil {
					m.bridge = ag
				}
			}
		}
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: fmt.Sprintf("已连接大模型服务 [%s]，平台: %s, 模型: %s。直接输入问题即可开始多轮对话 (输入 /model 可切换模型平台)。", cfgPath, m.config.Provider, m.config.ModelName),
		})
	} else {
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: "欢迎使用 coustea！可在下方输入框直接对话；如需配置模型，可随时输入 /model 调出配置向导。",
		})
	}

	m.viewport.SetContent(m.renderChatMessages())

	return m
}

// Init 实现 tea.Model 接口
func (m Model) Init() tea.Cmd {
	return tea.Batch(textinput.Blink, m.spinner.Tick)
}

// Update 事件分发总入口
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case spinner.TickMsg:
		if m.isGenerating {
			var cmd tea.Cmd
			m.spinner, cmd = m.spinner.Update(msg)
			return m, cmd
		}

	case tea.MouseMsg:
		if m.state == stateChat && m.viewportReady {
			var cmd tea.Cmd
			m.viewport, cmd = m.viewport.Update(msg)
			return m, cmd
		}

	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyCtrlC:
			// 若当前正在流式生成，按下 Ctrl+C 优先中断当前会话生成，不退出应用
			if m.isGenerating {
				if m.cancel != nil {
					m.cancel()
					m.cancel = nil
				}
				m.isGenerating = false
				m.activeToolName = ""
				m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
				m.chatInput.Focus()
				if len(m.messages) > 0 {
					m.messages[len(m.messages)-1].Content += "\n[用户已中断当前生成]"
				}
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}
			// 非生成状态下，Ctrl+C 全局立即退出应用
			return m, tea.Quit

		case tea.KeyCtrlD:
			// 在选单页面或聊天输入框为空时，Ctrl+D 触发退出
			if m.state != stateChat || m.chatInput.Value() == "" {
				return m, tea.Quit
			}

		case tea.KeyEsc:
			// 若在生成中按 Esc，同样支持快速中断当前生成
			if m.isGenerating {
				if m.cancel != nil {
					m.cancel()
					m.cancel = nil
				}
				m.isGenerating = false
				m.activeToolName = ""
				m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
				m.chatInput.Focus()
				if len(m.messages) > 0 {
					m.messages[len(m.messages)-1].Content += "\n[用户已中断当前生成]"
				}
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.chatInput.Width = max(40, msg.Width-10)

		headerHeight := 4
		footerHeight := 8
		if m.pendingPrompt != nil {
			footerHeight += 8
		}
		vpHeight := max(6, msg.Height-headerHeight-footerHeight)
		m.viewport.Width = max(40, msg.Width-2)
		m.viewport.Height = vpHeight
		m.viewportReady = true
		m.viewport.SetContent(m.renderChatMessages())
		m.viewport.GotoBottom()
		return m, nil

	case agentStreamEventMsg:
		if len(m.messages) == 0 {
			return m, nil
		}
		lastIdx := len(m.messages) - 1

		if msg.event.Err != nil {
			m.messages[lastIdx].Content += fmt.Sprintf("\n[出错: %v]", msg.event.Err)
			m.isGenerating = false
			m.activeToolName = ""
			m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
			m.chatInput.Focus()
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, nil
		}

		if msg.event.Type == agent.EventReasoningDelta {
			m.messages[lastIdx].ReasoningContent += msg.event.ReasoningDelta
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, waitForAgentEvent(msg.ch)
		}

		if msg.event.Type == agent.EventToolCallStart && msg.event.ToolCall != nil {
			m.activeToolName = msg.event.ToolCall.Name
			m.messages[lastIdx].ToolCalls = append(m.messages[lastIdx].ToolCalls, ToolCallRecord{
				ID:        msg.event.ToolCall.ID,
				Name:      msg.event.ToolCall.Name,
				Arguments: string(msg.event.ToolCall.Arguments),
				Running:   true,
			})
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
		}

		if msg.event.Type == agent.EventToolPermissionRequest && msg.event.PermissionPrompt != nil {
			m.pendingPrompt = msg.event.PermissionPrompt
			m.chatInput.Placeholder = "[等待权限决策] 请直接按 y (允许) / a (信任) / n (拒绝)"
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, waitForAgentEvent(msg.ch)
		}

		if msg.event.Type == agent.EventToolCallResult && msg.event.ToolResult != nil {
			m.activeToolName = ""
			tcs := m.messages[lastIdx].ToolCalls
			found := false
			for i := len(tcs) - 1; i >= 0; i-- {
				if tcs[i].ID == msg.event.ToolResult.ToolCallID || tcs[i].Name == msg.event.ToolResult.Name {
					tcs[i].Running = false
					tcs[i].Result = msg.event.ToolResult.Content
					tcs[i].IsError = msg.event.ToolResult.IsError
					found = true
					break
				}
			}
			if !found {
				m.messages[lastIdx].ToolCalls = append(m.messages[lastIdx].ToolCalls, ToolCallRecord{
					ID:      msg.event.ToolResult.ToolCallID,
					Name:    msg.event.ToolResult.Name,
					Result:  msg.event.ToolResult.Content,
					IsError: msg.event.ToolResult.IsError,
					Running: false,
				})
			}
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
		}

		if msg.event.Delta != "" {
			m.messages[lastIdx].Content += msg.event.Delta
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
		}

		if msg.event.Done {
			m.isGenerating = false
			m.activeToolName = ""
			m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
			m.chatInput.Focus()
			if msg.event.Usage != nil && msg.event.Usage.TotalTokens > 0 {
				m.messages[lastIdx].Usage = msg.event.Usage
			}
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, nil
		}

		return m, waitForAgentEvent(msg.ch)
	}

	// 根据当前状态分发至对应的模块
	switch m.state {
	case stateSelectModel:
		return m.updateSelectModel(msg)
	case stateInputAPIKey:
		return m.updateInputAPIKey(msg)
	case stateInputModel:
		return m.updateInputModel(msg)
	case stateChat:
		return m.updateChat(msg)
	}

	return m, nil
}

// View 界面渲染总入口
func (m Model) View() string {
	switch m.state {
	case stateSelectModel:
		return m.viewSelectModel()
	case stateInputAPIKey:
		return m.viewInputAPIKey()
	case stateInputModel:
		return m.viewInputModel()
	case stateChat:
		return m.viewChat()
	default:
		return ""
	}
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
