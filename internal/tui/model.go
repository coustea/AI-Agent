package tui

import (
	"fmt"
	"strings"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/gateway"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
)

// ======================== 模型配置相关逻辑 ========================

// updateSelectModel 处理类似官网例子的模型选择页（按上下键移动光标，Enter 选中）
func (m Model) updateSelectModel(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		// 快捷键判定
		switch msg.Type {
		case tea.KeyEsc:
			// 随时按 Esc 返回主线对话
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil
		case tea.KeyUp:
			if m.cursor > 0 {
				m.cursor--
			}
			return m, nil
		case tea.KeyDown:
			if m.cursor < len(m.choices)-1 {
				m.cursor++
			}
			return m, nil
		case tea.KeyEnter, tea.KeySpace:
			m.selected = m.cursor
			chosen := m.choices[m.selected]
			m.config.Provider = config.Provider(chosen)

			// 预设最新默认模型
			defaultModel := config.GetDefaultModelForProvider(m.config.Provider)
			m.config.ModelName = defaultModel
			m.modelInput.SetValue(defaultModel)

			// 切换到 API Key 输入状态
			m.state = stateInputAPIKey
			m.apiKeyInput.Focus()
			m.apiKeyInput.Reset()
			return m, textinput.Blink
		}

		// 字符键判定 (q, k, j)
		switch msg.String() {
		case "q":
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil
		case "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "j":
			if m.cursor < len(m.choices)-1 {
				m.cursor++
			}
		}
	}
	return m, nil
}

// updateInputAPIKey 处理 API Key 的输入
func (m Model) updateInputAPIKey(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyEsc:
			m.state = stateSelectModel
			return m, nil
		case tea.KeyEnter:
			keyVal := strings.TrimSpace(m.apiKeyInput.Value())
			if keyVal != "" || strings.ToLower(string(m.config.Provider)) == "llamacpp" {
				m.config.APIKey = keyVal
				// 切换到输入/确认模型名称状态
				m.state = stateInputModel
				m.modelInput.Focus()
				return m, textinput.Blink
			}
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.apiKeyInput, cmd = m.apiKeyInput.Update(msg)
	return m, cmd
}

// updateInputModel 处理模型名称输入/确认，并持久化到 json 文件
func (m Model) updateInputModel(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyEsc:
			m.state = stateInputAPIKey
			return m, nil
		case tea.KeyEnter:
			nameVal := strings.TrimSpace(m.modelInput.Value())
			if nameVal == "" {
				nameVal = config.GetDefaultModelForProvider(m.config.Provider)
			}
			m.config.ModelName = nameVal

			// 保存到 json 文件
			_ = config.SaveConfig(m.cfgPath, &m.config)

			// 自动根据新保存的配置更新 Gateway，优先通过 SetGateway 保留历史记忆
			if gw, err := gateway.NewGatewayFromConfig(&m.config); err == nil {
				if m.bridge != nil {
					m.bridge.SetGateway(gw)
				} else if ag, err := agent.NewAgent(gw, agent.WithDefaultTools()); err == nil {
					m.bridge = ag
				}
			}

			// 进入主聊天页面
			m.state = stateChat
			m.chatInput.Focus()
			m.chatInput.Reset()
			m.messages = append(m.messages, ChatMessage{
				Sender: "System",
				Content: fmt.Sprintf("已成功配置模型并保存至 %s！平台: %s, 模型: %s",
					m.cfgPath, m.config.Provider, m.config.ModelName),
			})
			return m, textinput.Blink
		}
	}

	var cmd tea.Cmd
	m.modelInput, cmd = m.modelInput.Update(msg)
	return m, cmd
}

// ======================== 模型配置相关页面视图 ========================

// viewSelectModel 渲染类似官网例子的模型选择页
func (m Model) viewSelectModel() string {
	var s strings.Builder

	s.WriteString(titleStyle.Render("╭─ coustea • 模型平台选择 ──────────────────────────────────────────╮") + "\n")
	s.WriteString("请选择要使用的大模型平台 (默认支持最新的 Gemini 和 DeepSeek)：\n\n")

	for i, choice := range m.choices {
		cursor := " "
		if m.cursor == i {
			cursor = cursorStyle.Render(">")
		}

		checked := " "
		if m.selected == i {
			checked = selectedStyle.Render("x")
		}

		desc := ""
		switch strings.ToLower(choice) {
		case "llamacpp", "llama":
			desc = dimStyle.Render(" (本地 llama.cpp HTTP 服务 - 默认: " + config.DefaultLlamaCppBaseURL + ")")
		case "deepseek", "ds":
			desc = dimStyle.Render(" (DeepSeek 官网最新 - Flash: " + config.DefaultDeepSeekModel + ", Pro: " + config.DeepSeekProModel + ")")
		case "gemini", "google":
			desc = dimStyle.Render(" (Google Gemini 官网最新 - Flash: " + config.DefaultGeminiModel + ", Pro: " + config.GeminiProModel + ")")
		}

		s.WriteString(fmt.Sprintf("  %s [%s] %s%s\n", cursor, checked, choice, desc))
	}

	s.WriteString("\n" + footerStyle.Render("操作说明: [↑/k] 向上移动  [↓/j] 向下移动  [Enter/空格] 选中并配置  [Esc/q] 取消并返回对话") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}

// viewInputAPIKey 渲染 API Key 输入页
func (m Model) viewInputAPIKey() string {
	var s strings.Builder

	provider := string(m.config.Provider)
	s.WriteString(titleStyle.Render(fmt.Sprintf("╭─ coustea • 配置 %s API Key ─────────────────────────────────────────╮", provider)) + "\n")
	s.WriteString(fmt.Sprintf("请输入 %s 的 API Key：\n\n", provider))
	s.WriteString("  " + m.apiKeyInput.View() + "\n\n")
	s.WriteString(footerStyle.Render("  [Enter] 确认下一步  [Esc] 返回选择平台  [Ctrl+C] 退出") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}

// viewInputModel 渲染模型名称输入/确认页
func (m Model) viewInputModel() string {
	var s strings.Builder

	provider := string(m.config.Provider)
	defaultModel := config.GetDefaultModelForProvider(m.config.Provider)

	s.WriteString(titleStyle.Render(fmt.Sprintf("╭─ coustea • 配置 %s 模型名称 ────────────────────────────────────────╮", provider)) + "\n")
	s.WriteString(fmt.Sprintf("请输入或修改模型名称（直接按 Enter 使用最新默认值: %s）：\n\n", defaultModel))
	s.WriteString("  " + m.modelInput.View() + "\n\n")
	s.WriteString(footerStyle.Render("  [Enter] 保存至 config.json 并进入对话  [Esc] 返回上一步  [Ctrl+C] 退出") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}
