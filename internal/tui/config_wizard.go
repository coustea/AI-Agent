package tui

import (
	"fmt"
	"strings"

	"my-agent/internal/config"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// handleModelCommand 集中处理模型配置相关的快捷指令（呼出向导看板或快速切换模型）
func (m Model) handleModelCommand(arg string) (Model, tea.Cmd) {
	m.chatInput.Reset()

	// 1. 无参数：呼出三要素分步配置向导
	if strings.TrimSpace(arg) == "" {
		m.wizardBaseURL = ""
		m.wizardAPIKey = ""
		m.wizardModel = ""

		cfg := m.agent.Config()
		m.baseURLInput.Reset()
		if cfg.BaseURL != "" {
			m.baseURLInput.Placeholder = cfg.BaseURL
		} else {
			m.baseURLInput.Placeholder = "https://api.openai.com/v1"
		}

		m.state = stateInputBaseURL
		m.baseURLInput.Focus()
		return m, textinput.Blink
	}

	// 2. 带参数：作为模型名称快速切换
	targetModel := strings.TrimSpace(arg)
	if err := m.agent.UpdateConfig("", "", targetModel); err != nil {
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: fmt.Sprintf("[切换模型失败: %v (可输入 /model 调出配置向导)]", err),
		})
	} else {
		cfg := m.agent.Config()
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: fmt.Sprintf("已成功切换模型！当前端点: %s, 模型: %s", cfg.BaseURL, cfg.ModelName),
		})
	}

	if m.viewportReady {
		m.viewport.SetContent(m.renderChatMessages())
		m.viewport.GotoBottom()
	}
	return m, nil
}

// ======================== 步骤 1: Base URL 输入 ========================

func (m Model) updateInputBaseURL(msg tea.Msg) (tea.Model, tea.Cmd) {
	if keyMsg, ok := msg.(tea.KeyMsg); ok {
		switch keyMsg.Type {
		case tea.KeyEsc:
			m.wizardBaseURL = ""
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil

		case tea.KeyEnter:
			val := strings.TrimSpace(m.baseURLInput.Value())
			if val == "" {
				val = m.baseURLInput.Placeholder
			}
			if val == "" {
				val = "https://api.openai.com/v1"
			}
			// 去除结尾斜杠（非根路径）
			val = strings.TrimRight(val, "/")
			m.wizardBaseURL = val

			// 进入步骤 2: API Key
			m.state = stateInputAPIKey
			m.apiKeyInput.Reset()
			cfg := m.agent.Config()
			if config.IsLocalURL(val) {
				m.apiKeyInput.Placeholder = "本地端点免鉴权，直接按 Enter 跳过"
			} else if cfg.HasAPIKey {
				m.apiKeyInput.Placeholder = "已有密钥，直接按 Enter 沿用已有密钥"
			} else {
				m.apiKeyInput.Placeholder = "在此粘贴或输入你的 API Key (按 Enter 确认)"
			}
			m.apiKeyInput.Focus()
			return m, textinput.Blink
		}
	}

	var cmd tea.Cmd
	m.baseURLInput, cmd = m.baseURLInput.Update(msg)
	return m, cmd
}

func (m Model) viewInputBaseURL() string {
	cardWidth := max(64, min(m.width-6, 80))
	var s strings.Builder

	badge := bentoTitleBadgeStyle.Render(" Tide ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(" 配置 OpenAI 服务端点 [1/3]")
	s.WriteString(fmt.Sprintf("%s %s\n\n", badge, title))

	s.WriteString("请输入兼容 OpenAI 协议的服务端点 (Base URL)：\n\n")
	s.WriteString("  " + m.baseURLInput.View() + "\n\n")

	hint := lipgloss.NewStyle().Foreground(colorTextMuted).Render(
		"常见端点参考：\n" +
			"  • 官方端点: https://api.openai.com/v1\n" +
			"  • DeepSeek: https://api.deepseek.com/v1\n" +
			"  • Google Gemini: https://generativelanguage.googleapis.com/v1beta/openai\n" +
			"  • 本地端点 (Ollama/llama.cpp): http://127.0.0.1:11434/v1 或 http://127.0.0.1:8080/v1",
	)
	s.WriteString(hint + "\n\n")

	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(30, cardWidth-8)))
	s.WriteString(divider + "\n")

	footer := fmt.Sprintf("%s 下一步 (API Key)  %s 取消并返回对话  %s 退出",
		keycapPillStyle.Render("[Enter]"),
		keycapPillStyle.Render("[Esc]"),
		keycapPillStyle.Render("[Ctrl+C]"),
	)
	s.WriteString(footerStyle.Render(footer))

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorBrand).
		Background(colorSurface).
		Padding(1, 2).
		Width(cardWidth).
		Render(s.String()) + "\n"
}

// ======================== 步骤 2: API Key 输入 ========================

func (m Model) updateInputAPIKey(msg tea.Msg) (tea.Model, tea.Cmd) {
	if keyMsg, ok := msg.(tea.KeyMsg); ok {
		switch keyMsg.Type {
		case tea.KeyEsc:
			m.wizardBaseURL = ""
			m.wizardAPIKey = ""
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil

		case tea.KeyEnter:
			val := strings.TrimSpace(m.apiKeyInput.Value())
			m.wizardAPIKey = val

			// 进入步骤 3: 模型名称
			m.state = stateInputModel
			m.modelInput.Reset()
			cfg := m.agent.Config()
			if cfg.ModelName != "" {
				m.modelInput.Placeholder = cfg.ModelName
			} else {
				m.modelInput.Placeholder = "例如 gpt-4o / deepseek-chat / qwen2.5-coder"
			}
			m.modelInput.Focus()
			return m, textinput.Blink
		}
	}

	var cmd tea.Cmd
	m.apiKeyInput, cmd = m.apiKeyInput.Update(msg)
	return m, cmd
}

func (m Model) viewInputAPIKey() string {
	cardWidth := max(64, min(m.width-6, 80))
	var s strings.Builder

	badge := bentoTitleBadgeStyle.Render(" Tide ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(" 配置 API 访问密钥 [2/3]")
	s.WriteString(fmt.Sprintf("%s %s\n\n", badge, title))

	endpointInfo := lipgloss.NewStyle().Foreground(colorCyan).Render("当前端点: " + m.wizardBaseURL)
	s.WriteString(endpointInfo + "\n\n")

	if config.IsLocalURL(m.wizardBaseURL) {
		s.WriteString("检测到本地端点无需鉴权密钥，直接按 Enter 跳过即可：\n\n")
	} else if m.agent.Config().HasAPIKey {
		s.WriteString("检测到已配置 API Key。直接按 Enter 沿用已有密钥，或输入新 Key 覆盖：\n\n")
	} else {
		s.WriteString("请输入 API Key：\n\n")
	}

	s.WriteString("  " + m.apiKeyInput.View() + "\n\n")

	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(30, cardWidth-8)))
	s.WriteString(divider + "\n")

	footer := fmt.Sprintf("%s 下一步 (模型规格)  %s 取消并返回对话  %s 退出",
		keycapPillStyle.Render("[Enter]"),
		keycapPillStyle.Render("[Esc]"),
		keycapPillStyle.Render("[Ctrl+C]"),
	)
	s.WriteString(footerStyle.Render(footer))

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorBrand).
		Background(colorSurface).
		Padding(1, 2).
		Width(cardWidth).
		Render(s.String()) + "\n"
}

// ======================== 步骤 3: Model 模型名称输入 ========================

func (m Model) updateInputModel(msg tea.Msg) (tea.Model, tea.Cmd) {
	if keyMsg, ok := msg.(tea.KeyMsg); ok {
		switch keyMsg.Type {
		case tea.KeyEsc:
			m.wizardBaseURL = ""
			m.wizardAPIKey = ""
			m.wizardModel = ""
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil

		case tea.KeyEnter:
			val := strings.TrimSpace(m.modelInput.Value())
			if val == "" {
				val = m.modelInput.Placeholder
			}
			if val == "" {
				// 未输入模型且无默认值
				return m, nil
			}

			// 提交配置更新
			if err := m.agent.UpdateConfig(m.wizardBaseURL, m.wizardAPIKey, val); err != nil {
				m.messages = append(m.messages, ChatMessage{
					Sender:  "System",
					Content: fmt.Sprintf("[配置保存失败: %v]", err),
				})
			} else {
				cfg := m.agent.Config()
				m.messages = append(m.messages, ChatMessage{
					Sender:  "System",
					Content: fmt.Sprintf("已成功更新模型配置！端点: %s, 模型: %s", cfg.BaseURL, cfg.ModelName),
				})
			}

			m.wizardBaseURL = ""
			m.wizardAPIKey = ""
			m.wizardModel = ""
			m.state = stateChat
			m.chatInput.Focus()
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.modelInput, cmd = m.modelInput.Update(msg)
	return m, cmd
}

func (m Model) viewInputModel() string {
	cardWidth := max(64, min(m.width-6, 80))
	var s strings.Builder

	badge := bentoTitleBadgeStyle.Render(" Tide ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(" 配置模型名称 (Model) [3/3]")
	s.WriteString(fmt.Sprintf("%s %s\n\n", badge, title))

	info := fmt.Sprintf("服务端点: %s", m.wizardBaseURL)
	s.WriteString(lipgloss.NewStyle().Foreground(colorCyan).Render(info) + "\n\n")

	s.WriteString("请输入模型名称 (Model Name)：\n\n")
	s.WriteString("  " + m.modelInput.View() + "\n\n")

	hint := lipgloss.NewStyle().Foreground(colorTextMuted).Render(
		"常见模型名称参考：\n" +
			"  • gpt-4o / gpt-4o-mini / o1 / o3-mini\n" +
			"  • deepseek-chat / deepseek-reasoner\n" +
			"  • gemini-2.5-flash / gemini-2.5-pro\n" +
			"  • qwen2.5-coder:7b / llama3.3:70b",
	)
	s.WriteString(hint + "\n\n")

	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(30, cardWidth-8)))
	s.WriteString(divider + "\n")

	footer := fmt.Sprintf("%s 保存并生效  %s 取消并返回对话  %s 退出",
		keycapPillStyle.Render("[Enter]"),
		keycapPillStyle.Render("[Esc]"),
		keycapPillStyle.Render("[Ctrl+C]"),
	)
	s.WriteString(footerStyle.Render(footer))

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorBrand).
		Background(colorSurface).
		Padding(1, 2).
		Width(cardWidth).
		Render(s.String()) + "\n"
}
