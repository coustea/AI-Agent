package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
)

// defaultModelForProvider 返回各厂商在 UI 中的建议默认模型
func defaultModelForProvider(provider string) string {
	switch strings.ToLower(provider) {
	case "deepseek", "ds":
		return "deepseek-chat"
	case "gemini", "google":
		return "gemini-2.5-flash"
	case "spark", "xfyun", "maas":
		return "lite"
	default:
		return "local-model"
	}
}

// isLocalProviderName 判断是否为免密钥本地服务
func isLocalProviderName(provider string) bool {
	p := strings.ToLower(provider)
	return p == "llamacpp" || p == "llama" || p == "local"
}

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
			m.currentProvider = chosen

			// 若当前 agent 激活的是该厂商，拉取已有模型名
			if m.agent != nil {
				cfgView := m.agent.Config()
				if strings.EqualFold(cfgView.Provider, chosen) {
					m.currentModel = cfgView.ModelName
				} else {
					m.currentModel = defaultModelForProvider(chosen)
				}
			} else {
				m.currentModel = defaultModelForProvider(chosen)
			}

			// 预设模型名称
			m.modelInput.SetValue(m.currentModel)

			// 切换到 API Key 输入状态
			m.state = stateInputAPIKey
			m.apiKeyInput.Focus()
			if m.currentAPIKey != "" {
				m.apiKeyInput.SetValue(m.currentAPIKey)
				m.apiKeyInput.Placeholder = "已存在输入的 API Key (直接按 Enter 保留，或输入新 Key)"
			} else {
				m.apiKeyInput.Reset()
				m.apiKeyInput.Placeholder = "在此粘贴或输入你的 API Key (按 Enter 确认)"
			}
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
			if keyVal == "" && m.currentAPIKey != "" {
				keyVal = m.currentAPIKey
			}

			if keyVal != "" || isLocalProviderName(m.currentProvider) {
				m.currentAPIKey = keyVal
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

// updateInputModel 处理模型名称输入/确认，并委托 Agent 内核持久化落盘
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
				nameVal = m.currentModel
				if nameVal == "" {
					nameVal = defaultModelForProvider(m.currentProvider)
				}
			}
			m.currentModel = nameVal

			// 委托 Agent 热切换网关与模型（由内核负责校验并落盘 config.json）
			if m.agent != nil {
				if err := m.agent.UpdateConfig(m.currentProvider, m.currentAPIKey, m.currentModel); err != nil {
					m.messages = append(m.messages, ChatMessage{
						Sender:  "System",
						Content: fmt.Sprintf("[配置切换失败: %v]", err),
					})
				} else {
					cfgView := m.agent.Config()
					m.currentModel = cfgView.ModelName
					m.messages = append(m.messages, ChatMessage{
						Sender:  "System",
						Content: fmt.Sprintf("已成功切换模型！当前平台: %s, 模型: %s", cfgView.Provider, cfgView.ModelName),
					})
				}
			}

			// 进入主聊天页面
			m.state = stateChat
			m.chatInput.Focus()
			m.chatInput.Reset()
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
	s.WriteString("请选择要使用的大模型平台 (支持本地记住各平台密钥，切换无需重复输入)：\n\n")

	for i, choice := range m.choices {
		cursor := " "
		if m.cursor == i {
			cursor = cursorStyle.Render(">")
		}

		checked := " "
		if m.selected == i {
			checked = selectedStyle.Render("x")
		}

		savedTag := ""
		if m.agent != nil {
			cfgView := m.agent.Config()
			if strings.EqualFold(cfgView.Provider, choice) && cfgView.HasAPIKey {
				savedTag = " [✔ 已配置]"
			}
		} else if isLocalProviderName(choice) {
			savedTag = " [✔ 已配置]"
		}

		desc := ""
		switch strings.ToLower(choice) {
		case "llamacpp", "llama":
			desc = dimStyle.Render(" (本地 llama.cpp HTTP 服务)")
		case "deepseek", "ds":
			desc = dimStyle.Render(" (DeepSeek 官网最新 - Flash: deepseek-chat)")
		case "gemini", "google":
			desc = dimStyle.Render(" (Google Gemini 官网最新 - Flash: gemini-2.5-flash)")
		case "spark", "xfyun", "maas":
			desc = dimStyle.Render(" (讯飞星辰 MaaS 平台 - 默认: lite)")
		}

		s.WriteString(fmt.Sprintf("  %s [%s] %s%s%s\n", cursor, checked, choice, savedTag, desc))
	}

	s.WriteString("\n" + footerStyle.Render("操作说明: [↑/k] 向上移动  [↓/j] 向下移动  [Enter/空格] 选中并配置  [Esc/q] 取消并返回对话  [Ctrl+C] 退出") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}

// viewInputAPIKey 渲染 API Key 输入页
func (m Model) viewInputAPIKey() string {
	var s strings.Builder

	provider := m.currentProvider
	s.WriteString(titleStyle.Render(fmt.Sprintf("╭─ coustea • 配置 %s API Key ─────────────────────────────────────────╮", provider)) + "\n")

	if m.currentAPIKey != "" {
		s.WriteString(fmt.Sprintf("检测到已输入 %s 的 API Key。直接按 Enter 保留，或输入新 Key 覆盖：\n\n", provider))
	} else if isLocalProviderName(provider) {
		s.WriteString(fmt.Sprintf("本地服务 %s 无需鉴权密钥，直接按 Enter 继续即可：\n\n", provider))
	} else {
		s.WriteString(fmt.Sprintf("请输入 %s 的 API Key：\n\n", provider))
	}

	s.WriteString("  " + m.apiKeyInput.View() + "\n\n")
	s.WriteString(footerStyle.Render("  [Enter] 确认下一步  [Esc] 返回选择平台  [Ctrl+C] 退出") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}

// viewInputModel 渲染模型名称输入/确认页
func (m Model) viewInputModel() string {
	var s strings.Builder

	provider := m.currentProvider
	defaultModel := m.currentModel
	if defaultModel == "" {
		defaultModel = defaultModelForProvider(provider)
	}

	s.WriteString(titleStyle.Render(fmt.Sprintf("╭─ coustea • 配置 %s 模型名称 ────────────────────────────────────────╮", provider)) + "\n")
	s.WriteString(fmt.Sprintf("请输入或修改模型名称（直接按 Enter 使用默认值: %s）：\n\n", defaultModel))
	s.WriteString("  " + m.modelInput.View() + "\n\n")
	s.WriteString(footerStyle.Render("  [Enter] 保存配置并进入对话  [Esc] 返回上一步  [Ctrl+C] 退出") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}
