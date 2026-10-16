package tui

import (
	"fmt"
	"strings"

	"my-agent/internal/protocol"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// getProviders 从 Agent 协议契约获取完整的平台状态列表，支持离线/测试桩兜底
func (m Model) getProviders() []protocol.ProviderInfo {
	if m.agent != nil {
		cfgView := m.agent.Config()
		if len(cfgView.Providers) > 0 {
			return cfgView.Providers
		}
	}
	// 针对未注入 Agent 或轻量测试桩的兜底
	res := make([]protocol.ProviderInfo, 0, len(m.choices))
	for _, c := range m.choices {
		isLocal := isLocalProviderName(c)
		res = append(res, protocol.ProviderInfo{
			ID:           c,
			Name:         c,
			IsLocal:      isLocal,
			IsConfigured: isLocal,
			CurrentModel: "default-model",
		})
	}
	return res
}

// isLocalProviderName 判断是否为免密钥本地服务
func isLocalProviderName(provider string) bool {
	p := strings.ToLower(strings.TrimSpace(provider))
	return p == "llamacpp" || p == "llama" || p == "local"
}

// syncActiveProvider 同步当前激活厂商并重置光标与选中索引
func (m *Model) syncActiveProvider(provider string) {
	m.currentProvider = provider
	for i, c := range m.choices {
		if strings.EqualFold(c, provider) {
			m.selected = i
			m.cursor = i
			break
		}
	}
}

// ======================== 模型配置相关逻辑 ========================

// updateSelectModel 处理平台看板（按上下键移动光标，Enter 一键直切，m 选规格，e 改密钥）
func (m Model) updateSelectModel(msg tea.Msg) (tea.Model, tea.Cmd) {
	providers := m.getProviders()
	if len(providers) == 0 {
		m.state = stateChat
		m.chatInput.Focus()
		return m, nil
	}

	if m.cursor >= len(providers) {
		m.cursor = len(providers) - 1
	}

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyEsc:
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil

		case tea.KeyUp:
			if m.cursor > 0 {
				m.cursor--
			}
			return m, nil

		case tea.KeyDown:
			if m.cursor < len(providers)-1 {
				m.cursor++
			}
			return m, nil

		case tea.KeyTab, tea.KeyRight:
			// 按 Tab 或向右方向键展开当前厂商的模型规格清单
			return m.openModelPresetMenu(providers[m.cursor])

		case tea.KeyEnter:
			p := providers[m.cursor]
			m.currentProvider = p.ID
			m.currentModel = p.CurrentModel

			if p.IsConfigured {
				// 一键极速切换 (Fast Switch)！已保存密钥或本地免密，直接切换并返回对话
				if m.agent != nil {
					if err := m.agent.UpdateConfig(p.ID, "", p.CurrentModel); err != nil {
						m.messages = append(m.messages, ChatMessage{
							Sender:  "System",
							Content: fmt.Sprintf("[配置切换失败: %v]", err),
						})
					} else {
						cfgView := m.agent.Config()
						m.syncActiveProvider(cfgView.Provider)
						m.currentModel = cfgView.ModelName
						m.messages = append(m.messages, ChatMessage{
							Sender:  "System",
							Content: fmt.Sprintf("已成功切换模型！当前平台: %s, 模型: %s", cfgView.Provider, cfgView.ModelName),
						})
					}
				}
				m.state = stateChat
				m.chatInput.Focus()
				m.chatInput.Reset()
				return m, nil
			}

			// 未配置密钥，跳转进入 API Key 输入
			m.state = stateInputAPIKey
			m.apiKeyInput.Focus()
			m.apiKeyInput.Reset()
			m.apiKeyInput.Placeholder = fmt.Sprintf("请输入 %s 的 API Key (按 Enter 确认)", p.Name)
			return m, textinput.Blink
		}

		// 字符快捷键处理
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
			if m.cursor < len(providers)-1 {
				m.cursor++
			}
		case "m":
			// 按 'm' 键选择具体模型规格
			return m.openModelPresetMenu(providers[m.cursor])
		case "e":
			// 按 'e' 键修改/重置当前平台的 API Key
			p := providers[m.cursor]
			m.currentProvider = p.ID
			m.currentModel = p.CurrentModel
			m.state = stateInputAPIKey
			m.apiKeyInput.Focus()
			m.apiKeyInput.Reset()
			if p.IsConfigured && !p.IsLocal {
				m.apiKeyInput.Placeholder = "已存在保存的 API Key (直接按 Enter 保留，或输入新 Key 覆盖)"
			} else {
				m.apiKeyInput.Placeholder = fmt.Sprintf("请输入 %s 的 API Key (按 Enter 确认)", p.Name)
			}
			return m, textinput.Blink
		}
	}
	return m, nil
}

// openModelPresetMenu 打开指定厂商的预设模型规格菜单
func (m Model) openModelPresetMenu(p protocol.ProviderInfo) (tea.Model, tea.Cmd) {
	m.currentProvider = p.ID
	m.currentModel = p.CurrentModel
	m.presetChoices = nil
	m.presetChoices = append(m.presetChoices, p.RecommendedModels...)
	m.presetChoices = append(m.presetChoices, "[+] 自定义输入模型名称...")

	m.presetCursor = 0
	for i, choice := range m.presetChoices {
		if choice == p.CurrentModel {
			m.presetCursor = i
			break
		}
	}

	m.state = stateSelectModelPreset
	return m, nil
}

// updateSelectModelPreset 处理模型规格预设列表的点选
func (m Model) updateSelectModelPreset(msg tea.Msg) (tea.Model, tea.Cmd) {
	if len(m.presetChoices) == 0 {
		m.state = stateSelectModel
		return m, nil
	}

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyEsc, tea.KeyLeft:
			// 返回平台选择看板
			m.state = stateSelectModel
			return m, nil

		case tea.KeyUp:
			if m.presetCursor > 0 {
				m.presetCursor--
			}
			return m, nil

		case tea.KeyDown:
			if m.presetCursor < len(m.presetChoices)-1 {
				m.presetCursor++
			}
			return m, nil

		case tea.KeyEnter:
			if m.presetCursor >= 0 && m.presetCursor < len(m.presetChoices) {
				chosen := m.presetChoices[m.presetCursor]
				if chosen == "[+] 自定义输入模型名称..." {
					m.state = stateInputModel
					m.modelInput.Focus()
					m.modelInput.Reset()
					m.modelInput.Placeholder = fmt.Sprintf("输入 %s 模型名称 (当前: %s)", m.currentProvider, m.currentModel)
					return m, textinput.Blink
				}

				m.currentModel = chosen

				// 检查当前平台是否已就绪 (新输入 Key、已存 Key 或本地)
				isConfigured := m.currentAPIKey != "" || isLocalProviderName(m.currentProvider)
				if !isConfigured {
					for _, p := range m.getProviders() {
						if p.ID == m.currentProvider && p.IsConfigured {
							isConfigured = true
							break
						}
					}
				}

				if !isConfigured {
					// 平台未配置 API Key，前往输入
					m.state = stateInputAPIKey
					m.apiKeyInput.Focus()
					m.apiKeyInput.Reset()
					m.apiKeyInput.Placeholder = fmt.Sprintf("请输入 %s 的 API Key (按 Enter 确认)", m.currentProvider)
					return m, textinput.Blink
				}

				// 平台已就绪，立即热切换模型并返回对话
				if m.agent != nil {
					if err := m.agent.UpdateConfig(m.currentProvider, m.currentAPIKey, m.currentModel); err != nil {
						m.messages = append(m.messages, ChatMessage{
							Sender:  "System",
							Content: fmt.Sprintf("[配置切换失败: %v]", err),
						})
					} else {
						cfgView := m.agent.Config()
						m.syncActiveProvider(cfgView.Provider)
						m.currentModel = cfgView.ModelName
						m.messages = append(m.messages, ChatMessage{
							Sender:  "System",
							Content: fmt.Sprintf("已成功切换模型！当前平台: %s, 模型: %s", cfgView.Provider, cfgView.ModelName),
						})
					}
				}

				m.state = stateChat
				m.chatInput.Focus()
				m.chatInput.Reset()
				return m, nil
			}
		}

		// 字符快捷键处理
		switch msg.String() {
		case "q":
			m.state = stateSelectModel
			return m, nil
		case "k":
			if m.presetCursor > 0 {
				m.presetCursor--
			}
		case "j":
			if m.presetCursor < len(m.presetChoices)-1 {
				m.presetCursor++
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
			if keyVal != "" {
				m.currentAPIKey = keyVal
			}

			// 验证当前是否有可用密钥 (用户刚输入的、之前保存过的、或本地服务)
			hasKey := m.currentAPIKey != "" || isLocalProviderName(m.currentProvider)
			if !hasKey {
				for _, p := range m.getProviders() {
					if p.ID == m.currentProvider && p.IsConfigured {
						hasKey = true
						break
					}
				}
			}

			if hasKey {
				// 引导进入模型规格点选菜单，让用户选择/确认要激活的模型规格
				var targetP protocol.ProviderInfo
				for _, p := range m.getProviders() {
					if p.ID == m.currentProvider {
						targetP = p
						break
					}
				}
				if targetP.ID == "" {
					targetP = protocol.ProviderInfo{
						ID:                m.currentProvider,
						Name:              m.currentProvider,
						CurrentModel:      m.currentModel,
						RecommendedModels: []string{m.currentModel},
					}
				}
				return m.openModelPresetMenu(targetP)
			}
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.apiKeyInput, cmd = m.apiKeyInput.Update(msg)
	return m, cmd
}

// updateInputModel 处理自定义模型名称输入，并委托 Agent 内核持久化落盘
func (m Model) updateInputModel(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyEsc:
			m.state = stateSelectModelPreset
			return m, nil
		case tea.KeyEnter:
			nameVal := strings.TrimSpace(m.modelInput.Value())
			if nameVal == "" {
				nameVal = m.currentModel
			}
			if nameVal != "" {
				m.currentModel = nameVal

				if m.agent != nil {
					if err := m.agent.UpdateConfig(m.currentProvider, m.currentAPIKey, m.currentModel); err != nil {
						m.messages = append(m.messages, ChatMessage{
							Sender:  "System",
							Content: fmt.Sprintf("[配置切换失败: %v]", err),
						})
					} else {
						cfgView := m.agent.Config()
						m.syncActiveProvider(cfgView.Provider)
						m.currentModel = cfgView.ModelName
						m.messages = append(m.messages, ChatMessage{
							Sender:  "System",
							Content: fmt.Sprintf("已成功切换模型！当前平台: %s, 模型: %s", cfgView.Provider, cfgView.ModelName),
						})
					}
				}

				m.state = stateChat
				m.chatInput.Focus()
				m.chatInput.Reset()
				return m, textinput.Blink
			}
		}
	}

	var cmd tea.Cmd
	m.modelInput, cmd = m.modelInput.Update(msg)
	return m, cmd
}

// ======================== 模型配置相关页面视图 ========================

// viewSelectModel 渲染平台总览与状态看板
func (m Model) viewSelectModel() string {
	var s strings.Builder

	s.WriteString(titleStyle.Render("╭─ coustea • 大模型平台与服务看板 ──────────────────────────────────╮") + "\n")
	s.WriteString("请选择大模型平台 (已就绪平台按 Enter 一键直切，按 m 可选择具体规格)：\n\n")

	providers := m.getProviders()
	activeProvider := ""
	if m.agent != nil {
		activeProvider = m.agent.Config().Provider
	}

	statusReadyStyle := lipgloss.NewStyle().Bold(true).Foreground(colorGreen)
	statusUnsetStyle := lipgloss.NewStyle().Foreground(colorDim)

	for i, p := range providers {
		cursor := " "
		if m.cursor == i {
			cursor = cursorStyle.Render(">")
		}

		checked := " "
		if strings.EqualFold(p.ID, activeProvider) || (activeProvider == "" && m.selected == i) {
			checked = selectedStyle.Render("x")
		}

		statusBadge := ""
		if p.IsConfigured {
			statusBadge = statusReadyStyle.Render("● [已就绪]")
		} else {
			statusBadge = statusUnsetStyle.Render("○ [未配置]")
		}

		desc := ""
		if p.Description != "" {
			desc = dimStyle.Render(fmt.Sprintf(" (%s)", p.Description))
		}

		modelHint := ""
		if p.CurrentModel != "" {
			modelHint = lipgloss.NewStyle().Foreground(colorYellow).Render(fmt.Sprintf(" [模型: %s]", p.CurrentModel))
		}

		s.WriteString(fmt.Sprintf("  %s [%s] %-14s %s%s%s\n", cursor, checked, p.Name, statusBadge, modelHint, desc))
	}

	s.WriteString("\n" + footerStyle.Render("操作说明: [Enter] 一键直切  [m/Tab] 选模型规格  [e] 修改API Key  [↑/k, ↓/j] 移动  [Esc/q] 返回对话") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}

// viewSelectModelPreset 渲染预设模型规格点选菜单
func (m Model) viewSelectModelPreset() string {
	var s strings.Builder

	pName := m.currentProvider
	for _, p := range m.getProviders() {
		if p.ID == m.currentProvider {
			pName = p.Name
			break
		}
	}

	s.WriteString(titleStyle.Render(fmt.Sprintf("╭─ coustea • 选择 %s 模型规格 ──────────────────────────────────────╮", pName)) + "\n")
	s.WriteString("请按上下键点选要激活的模型规格 (Enter 确认生效)：\n\n")

	for i, choice := range m.presetChoices {
		cursor := " "
		if m.presetCursor == i {
			cursor = cursorStyle.Render(">")
		}

		checked := " "
		if choice == m.currentModel {
			checked = selectedStyle.Render("*")
		}

		itemStyled := choice
		if choice == "[+] 自定义输入模型名称..." {
			itemStyled = lipgloss.NewStyle().Foreground(colorYellow).Render(choice)
		} else if choice == m.currentModel {
			itemStyled = lipgloss.NewStyle().Bold(true).Foreground(colorCyan).Render(choice) + dimStyle.Render(" (当前激活)")
		}

		s.WriteString(fmt.Sprintf("  %s [%s] %s\n", cursor, checked, itemStyled))
	}

	s.WriteString("\n" + footerStyle.Render("操作说明: [Enter] 确认切换并返回对话  [Esc/q] 返回平台列表  [Ctrl+C] 退出") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}

// viewInputAPIKey 渲染 API Key 输入页
func (m Model) viewInputAPIKey() string {
	var s strings.Builder

	provider := m.currentProvider
	for _, p := range m.getProviders() {
		if p.ID == m.currentProvider {
			provider = p.Name
			break
		}
	}

	s.WriteString(titleStyle.Render(fmt.Sprintf("╭─ coustea • 配置 %s API Key ─────────────────────────────────────────╮", provider)) + "\n")

	if m.currentAPIKey != "" {
		s.WriteString(fmt.Sprintf("检测到已输入 %s 的 API Key。直接按 Enter 保留，或输入新 Key 覆盖：\n\n", provider))
	} else if isLocalProviderName(m.currentProvider) {
		s.WriteString(fmt.Sprintf("本地服务 %s 无需鉴权密钥，直接按 Enter 继续即可：\n\n", provider))
	} else {
		s.WriteString(fmt.Sprintf("请输入 %s 的 API Key：\n\n", provider))
	}

	s.WriteString("  " + m.apiKeyInput.View() + "\n\n")
	s.WriteString(footerStyle.Render("  [Enter] 确认下一步  [Esc] 返回平台列表  [Ctrl+C] 退出") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}

// viewInputModel 渲染自定义模型名称输入/确认页
func (m Model) viewInputModel() string {
	var s strings.Builder

	provider := m.currentProvider
	for _, p := range m.getProviders() {
		if p.ID == m.currentProvider {
			provider = p.Name
			break
		}
	}

	s.WriteString(titleStyle.Render(fmt.Sprintf("╭─ coustea • 配置 %s 自定义模型 ──────────────────────────────────────╮", provider)) + "\n")
	s.WriteString(fmt.Sprintf("请输入自定义模型名称（直接按 Enter 使用当前值: %s）：\n\n", m.currentModel))
	s.WriteString("  " + m.modelInput.View() + "\n\n")
	s.WriteString(footerStyle.Render("  [Enter] 保存配置并进入对话  [Esc] 返回规格列表  [Ctrl+C] 退出") + "\n")
	s.WriteString(titleStyle.Render("╰───────────────────────────────────────────────────────────────────╯") + "\n")

	return s.String()
}

// handleModelCommand 集中处理模型配置相关的快捷指令（呼出向导看板或快速切换模型）
func (m Model) handleModelCommand(arg string) (Model, tea.Cmd) {
	m.chatInput.Reset()

	// 1. 无参数：直接呼出全屏平台选择看板
	if strings.TrimSpace(arg) == "" {
		m.state = stateSelectModel
		if m.agent != nil {
			cfgView := m.agent.Config()
			m.syncActiveProvider(cfgView.Provider)
		}
		m.cursor = m.selected
		return m, nil
	}

	if m.agent == nil {
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: "[未连接智能体内核，无法切换模型]",
		})
		return m, nil
	}

	// 2. 尝试匹配平台名称或常见别名
	pKey := strings.ToLower(strings.TrimSpace(arg))
	cfgView := m.agent.Config()
	var targetProvider *protocol.ProviderInfo
	for i := range cfgView.Providers {
		p := &cfgView.Providers[i]
		if strings.EqualFold(p.ID, pKey) ||
			(p.ID == "llamacpp" && (pKey == "llama" || pKey == "local")) ||
			(p.ID == "gemini" && pKey == "google") ||
			(p.ID == "deepseek" && pKey == "ds") ||
			(p.ID == "spark" && (pKey == "maas" || pKey == "xfyun")) {
			targetProvider = p
			break
		}
	}

	if targetProvider != nil {
		if targetProvider.IsConfigured {
			// 平台已就绪：极速静默直切
			if err := m.agent.UpdateConfig(targetProvider.ID, "", targetProvider.CurrentModel); err != nil {
				m.messages = append(m.messages, ChatMessage{
					Sender:  "System",
					Content: fmt.Sprintf("[切换平台失败: %v]", err),
				})
			} else {
				newView := m.agent.Config()
				m.syncActiveProvider(newView.Provider)
				m.currentModel = newView.ModelName
				m.messages = append(m.messages, ChatMessage{
					Sender:  "System",
					Content: fmt.Sprintf("已成功切换至大模型平台: %s (模型: %s)", targetProvider.Name, newView.ModelName),
				})
			}
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, nil
		}

		// 平台未就绪：引导进入 API Key 输入
		m.currentProvider = targetProvider.ID
		m.state = stateInputAPIKey
		m.apiKeyInput.Focus()
		m.apiKeyInput.Reset()
		m.apiKeyInput.Placeholder = fmt.Sprintf("请输入 %s 的 API Key (按 Enter 确认)", targetProvider.Name)
		return m, textinput.Blink
	}

	// 3. 作为具体模型名称智能识别与切换
	if err := m.agent.UpdateConfig("", "", arg); err != nil {
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: fmt.Sprintf("[切换模型失败: %v (输入 /model 可在配置看板中查看和设置)]", err),
		})
	} else {
		newView := m.agent.Config()
		m.syncActiveProvider(newView.Provider)
		m.currentModel = newView.ModelName
		m.messages = append(m.messages, ChatMessage{
			Sender:  "System",
			Content: fmt.Sprintf("已成功切换模型！当前平台: %s, 模型: %s", newView.Provider, newView.ModelName),
		})
	}

	if m.viewportReady {
		m.viewport.SetContent(m.renderChatMessages())
		m.viewport.GotoBottom()
	}
	return m, nil
}
