package tui

import (
	"context"
	"fmt"
	"strings"

	"my-agent/internal/agent"
	"my-agent/internal/protocol"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// sessionState 界面状态枚举
type sessionState int

const (
	stateSelectModel       sessionState = iota // 状态 1: 模型平台看板 (Enter 一键直切, m 选规格, e 改密钥)
	stateSelectModelPreset                     // 状态 2: 预设模型规格列表点选 (Flash/Pro/Reasoner/[+]自定义)
	stateInputAPIKey                           // 状态 3: 输入/修改 API Key
	stateInputModel                            // 状态 4: 输入自定义模型名称并保存
	stateChat                                  // 状态 5: 主聊天页面（在 chat.go 中处理）
)

// agentStreamEventMsg 封装来自 Agent 的单次纯数据流式事件
type agentStreamEventMsg struct {
	event protocol.Event
	ch    <-chan protocol.Event
}

func waitForAgentEvent(ch <-chan protocol.Event) tea.Cmd {
	return func() tea.Msg {
		event, ok := <-ch
		if !ok {
			return nil
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

	// 状态 1: 模型选择（官网示例风格，在 model.go 中处理）
	cursor          int
	choices         []string
	selected        int
	currentProvider string
	currentModel    string
	currentAPIKey   string

	// 状态 2: 模型规格预设选择菜单
	presetChoices []string
	presetCursor  int

	// 状态 3 & 4: 配置输入框（在 model.go 中处理）
	apiKeyInput textinput.Model
	modelInput  textinput.Model

	// 状态 4: 聊天输入框与消息列表（在 chat.go 中处理）
	chatInput    textinput.Model
	messages     []ChatMessage
	isGenerating bool               // 是否正在流式生成中
	cancel       context.CancelFunc // 当前流式会话的中断回调

	// 权限门禁待审批请求（基于纯数据 Protocol RequestID 关联）
	pendingPerm *protocol.PermissionRequest

	// 视口与动态指示器
	viewport       viewport.Model
	viewportReady  bool
	spinner        spinner.Model
	activeToolName string

	// 终端宽高适配
	width  int
	height int

	// 注入的 Agent 智能体核心接口
	agent agent.Agent
}

// NewModel 初始化并返回主 Model；ag 由装配入口保证非 nil，未就绪状态经 ConfigView 表达
func NewModel(ag agent.Agent) Model {
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

	cfgView := ag.Config()
	choices := []string{"llamacpp", "deepseek", "gemini", "spark"}
	if len(cfgView.AvailableProviders) > 0 {
		choices = cfgView.AvailableProviders
	}
	curProvider := cfgView.Provider
	curModel := cfgView.ModelName

	selectedIdx := 0
	for i, c := range choices {
		if strings.EqualFold(c, curProvider) {
			selectedIdx = i
			break
		}
	}

	m := Model{
		choices:         choices,
		selected:        selectedIdx,
		cursor:          selectedIdx,
		currentProvider: curProvider,
		currentModel:    curModel,
		apiKeyInput:     apiKeyInput,
		modelInput:      modelInput,
		chatInput:       chatInput,
		messages:        []ChatMessage{},
		agent:           ag,
		spinner:         sp,
		viewport:        vp,
	}

	// 主线永远是聊天对话页面（输入框交互）
	m.state = stateChat
	m.chatInput.Focus()

	if cfgView.HasAPIKey {
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: fmt.Sprintf("已连接大模型服务，平台: %s, 模型: %s。直接输入问题即可开始多轮对话 (输入 /model 可切换模型平台)。", cfgView.Provider, cfgView.ModelName),
		})
	} else {
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: "欢迎使用 coustea！当前模型尚未配置 API Key，可随时输入 /model 调出配置向导。",
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
		if m.pendingPerm != nil {
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

		switch msg.event.Type {
		case protocol.EventError:
			errMsg := msg.event.Error
			if errMsg == "" {
				errMsg = "未知异常"
			}
			m.messages[lastIdx].Content += fmt.Sprintf("\n[出错: %s]", errMsg)
			m.isGenerating = false
			m.activeToolName = ""
			m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
			m.chatInput.Focus()
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, nil

		case protocol.EventDone:
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

		case protocol.EventReasoningDelta:
			m.messages[lastIdx].ReasoningContent += msg.event.Reasoning
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, waitForAgentEvent(msg.ch)

		case protocol.EventDelta:
			m.messages[lastIdx].Content += msg.event.Delta
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, waitForAgentEvent(msg.ch)

		case protocol.EventToolCallStart:
			if msg.event.ToolCall != nil {
				m.activeToolName = msg.event.ToolCall.Name
				m.messages[lastIdx].ToolCalls = append(m.messages[lastIdx].ToolCalls, ToolCallRecord{
					ToolCall: *msg.event.ToolCall,
					Running:  true,
				})
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
			}
			return m, waitForAgentEvent(msg.ch)

		case protocol.EventToolCallResult:
			if msg.event.ToolResult != nil {
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
						ToolCall: protocol.ToolCall{
							ID:   msg.event.ToolResult.ToolCallID,
							Name: msg.event.ToolResult.Name,
						},
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
			return m, waitForAgentEvent(msg.ch)

		case protocol.EventPermissionReq:
			if msg.event.Permission != nil {
				m.pendingPerm = msg.event.Permission
				m.chatInput.Placeholder = "[等待权限决策] 请直接按 y (允许) / a (信任) / n (拒绝)"
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
			}
			return m, waitForAgentEvent(msg.ch)
		}

		return m, waitForAgentEvent(msg.ch)
	}

	// 根据当前状态分发至对应的模块
	switch m.state {
	case stateSelectModel:
		return m.updateSelectModel(msg)
	case stateSelectModelPreset:
		return m.updateSelectModelPreset(msg)
	case stateInputAPIKey:
		return m.updateInputAPIKey(msg)
	case stateInputModel:
		return m.updateInputModel(msg)
	case stateChat:
		return m.updateChat(msg)
	default:
		return m, nil
	}
}

// View 总渲染入口
func (m Model) View() string {
	switch m.state {
	case stateSelectModel:
		return m.viewSelectModel()
	case stateSelectModelPreset:
		return m.viewSelectModelPreset()
	case stateInputAPIKey:
		return m.viewInputAPIKey()
	case stateInputModel:
		return m.viewInputModel()
	case stateChat:
		return m.viewChat()
	default:
		return "未知界面状态"
	}
}
