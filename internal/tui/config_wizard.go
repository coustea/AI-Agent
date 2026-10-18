package tui

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"my-agent/internal/protocol"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// llamaCppProbeURL 本地推理服务默认探测端点
const llamaCppProbeURL = "http://127.0.0.1:8080/v1/models"

// probeLlamaCpp 探测本地 llama-server 是否就绪（2s 超时）。
// 返回非空提示文案表示未就绪；探测不阻断配置——服务可能稍后启动。
func probeLlamaCpp() string {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, llamaCppProbeURL, nil)
	if err != nil {
		return fmt.Sprintf("[提示] 本地服务探测失败: %v（配置已保留，可稍后启动 llama-server）", err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "[提示] 本地服务未就绪（连接失败），配置已保留。启动 llama-server 后即可直接对话。"
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Sprintf("[提示] 本地服务未就绪（HTTP %d），配置已保留。启动 llama-server 后即可直接对话。", resp.StatusCode)
	}
	return ""
}

// appendLocalProviderNotice 在切换到本地厂商后追加就绪探测提示
func (m *Model) appendLocalProviderNotice(provider string) {
	if !strings.EqualFold(strings.TrimSpace(provider), "llamacpp") {
		return
	}
	if notice := probeLlamaCpp(); notice != "" {
		m.messages = append(m.messages, ChatMessage{Sender: "System", Content: notice})
	}
}

// getProviders 从 Agent 协议契约获取完整的平台状态列表
func (m Model) getProviders() []protocol.ProviderInfo {
	return m.agent.Config().Providers
}

// isLocalProvider 判断指定平台是否为无需鉴权的本地服务（单源元数据驱动）
func (m Model) isLocalProvider(provider string) bool {
	for _, p := range m.getProviders() {
		if strings.EqualFold(p.ID, provider) {
			return p.IsLocal
		}
	}
	return false
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
			m.currentAPIKey = ""
			m.currentProvider = p.ID
			m.currentModel = p.CurrentModel

			if p.IsConfigured {
				// 一键极速切换 (Fast Switch)！已保存密钥或本地免密，直接切换并返回对话
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
					m.appendLocalProviderNotice(cfgView.Provider)
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
			m.currentAPIKey = ""
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
	if m.currentProvider != p.ID {
		m.currentAPIKey = ""
	}
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
				isConfigured := m.currentAPIKey != "" || m.isLocalProvider(m.currentProvider)
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
				apiKeyToSend := m.currentAPIKey
				m.currentAPIKey = ""
				if err := m.agent.UpdateConfig(m.currentProvider, apiKeyToSend, m.currentModel); err != nil {
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
					m.appendLocalProviderNotice(cfgView.Provider)
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
			m.currentAPIKey = keyVal

			// 验证当前是否有可用密钥 (用户刚输入的、之前保存过的、或本地服务)
			hasKey := m.currentAPIKey != "" || m.isLocalProvider(m.currentProvider)
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

				apiKeyToSend := m.currentAPIKey
				m.currentAPIKey = ""
				if err := m.agent.UpdateConfig(m.currentProvider, apiKeyToSend, m.currentModel); err != nil {
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
					m.appendLocalProviderNotice(cfgView.Provider)
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
	cardWidth := max(64, min(m.width-6, 88))
	var s strings.Builder

	// 标题区域
	titleBadge := bentoTitleBadgeStyle.Render(" Tide ")
	titleText := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(" 大模型平台与服务看板")
	subText := dimStyle.Render("请选择大模型平台 (已就绪平台按 Enter 一键直切，按 m 可选择具体规格)：")

	s.WriteString(fmt.Sprintf("%s %s\n%s\n\n", titleBadge, titleText, subText))

	providers := m.getProviders()
	activeProvider := m.agent.Config().Provider

	for i, p := range providers {
		cursor := "  "
		if m.cursor == i {
			cursor = cursorStyle.Render("❯ ")
		}

		checked := dimStyle.Render("[ ]")
		if strings.EqualFold(p.ID, activeProvider) || (activeProvider == "" && m.selected == i) {
			checked = selectedStyle.Render("[x]")
		}

		statusBadge := ""
		if p.IsConfigured {
			statusBadge = bentoReadyBadgeStyle.Render("● [已就绪]")
		} else {
			statusBadge = bentoUnsetBadgeStyle.Render("○ [未配置]")
		}

		desc := ""
		if p.Description != "" {
			desc = dimStyle.Render(fmt.Sprintf(" (%s)", p.Description))
		}

		modelHint := ""
		if p.CurrentModel != "" {
			modelHint = bentoModelChipStyle.Render(fmt.Sprintf(" [模型: %s]", p.CurrentModel))
		}

		nameStyled := p.Name
		if m.cursor == i {
			nameStyled = bentoActiveItemStyle.Render(p.Name)
		} else {
			nameStyled = bentoNormalItemStyle.Render(p.Name)
		}

		s.WriteString(fmt.Sprintf("%s%s %-16s %s%s%s\n", cursor, checked, nameStyled, statusBadge, modelHint, desc))
	}

	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(30, cardWidth-8)))
	s.WriteString("\n" + divider + "\n")

	// 底部操作快捷键胶囊 (包含原说明中的完整关键字，保证测试和操作完全兼容)
	footer := fmt.Sprintf("操作说明: %s 一键直切  %s 选模型规格  %s 修改API Key  %s 移动  %s 返回对话",
		keycapPillStyle.Render("[Enter]"),
		keycapPillStyle.Render("[m/Tab]"),
		keycapPillStyle.Render("[e]"),
		keycapPillStyle.Render("[↑/k, ↓/j]"),
		keycapPillStyle.Render("[Esc/q]"),
	)
	s.WriteString(footerStyle.Render(footer))

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorBorderActive).
		Background(colorSurface).
		Padding(1, 2).
		Width(cardWidth).
		Render(s.String()) + "\n"
}

// viewSelectModelPreset 渲染预设模型规格点选菜单
func (m Model) viewSelectModelPreset() string {
	cardWidth := max(64, min(m.width-6, 88))
	var s strings.Builder

	pName := m.currentProvider
	for _, p := range m.getProviders() {
		if p.ID == m.currentProvider {
			pName = p.Name
			break
		}
	}

	badge := bentoTitleBadgeStyle.Render(" Tide ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(fmt.Sprintf(" 选择 %s 模型规格", pName))
	sub := dimStyle.Render("请按上下键点选要激活的模型规格 (Enter 确认生效)：")

	s.WriteString(fmt.Sprintf("%s %s\n%s\n\n", badge, title, sub))

	for i, choice := range m.presetChoices {
		cursor := "  "
		if m.presetCursor == i {
			cursor = cursorStyle.Render("❯ ")
		}

		checked := dimStyle.Render("[ ]")
		if choice == m.currentModel {
			checked = selectedStyle.Render("[*]")
		}

		itemStyled := choice
		if choice == "[+] 自定义输入模型名称..." {
			itemStyled = lipgloss.NewStyle().Foreground(colorYellow).Render(choice)
		} else if choice == m.currentModel {
			itemStyled = lipgloss.NewStyle().Bold(true).Foreground(colorCyan).Render(choice) + dimStyle.Render(" (当前激活)")
		} else if m.presetCursor == i {
			itemStyled = bentoActiveItemStyle.Render(choice)
		} else {
			itemStyled = bentoNormalItemStyle.Render(choice)
		}

		s.WriteString(fmt.Sprintf("%s%s %s\n", cursor, checked, itemStyled))
	}

	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(30, cardWidth-8)))
	s.WriteString("\n" + divider + "\n")

	footer := fmt.Sprintf("操作说明: %s 确认切换并返回对话  %s 返回平台列表  %s 退出",
		keycapPillStyle.Render("[Enter]"),
		keycapPillStyle.Render("[Esc/q]"),
		keycapPillStyle.Render("[Ctrl+C]"),
	)
	s.WriteString(footerStyle.Render(footer))

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorBorderActive).
		Background(colorSurface).
		Padding(1, 2).
		Width(cardWidth).
		Render(s.String()) + "\n"
}

// viewInputAPIKey 渲染 API Key 输入页
func (m Model) viewInputAPIKey() string {
	cardWidth := max(64, min(m.width-6, 80))
	var s strings.Builder

	provider := m.currentProvider
	for _, p := range m.getProviders() {
		if p.ID == m.currentProvider {
			provider = p.Name
			break
		}
	}

	badge := bentoTitleBadgeStyle.Render(" Tide ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(fmt.Sprintf(" 配置 %s API Key", provider))
	s.WriteString(fmt.Sprintf("%s %s\n\n", badge, title))

	if m.currentAPIKey != "" {
		s.WriteString(fmt.Sprintf("检测到已输入 %s 的 API Key。直接按 Enter 保留，或输入新 Key 覆盖：\n\n", provider))
	} else if m.isLocalProvider(m.currentProvider) {
		s.WriteString(fmt.Sprintf("本地服务 %s 无需鉴权密钥，直接按 Enter 继续即可：\n\n", provider))
	} else {
		s.WriteString(fmt.Sprintf("请输入 %s 的 API Key：\n\n", provider))
	}

	s.WriteString("  " + m.apiKeyInput.View() + "\n\n")

	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(30, cardWidth-8)))
	s.WriteString(divider + "\n")

	footer := fmt.Sprintf("%s 确认下一步  %s 返回平台列表  %s 退出",
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

// viewInputModel 渲染自定义模型名称输入/确认页
func (m Model) viewInputModel() string {
	cardWidth := max(64, min(m.width-6, 80))
	var s strings.Builder

	provider := m.currentProvider
	for _, p := range m.getProviders() {
		if p.ID == m.currentProvider {
			provider = p.Name
			break
		}
	}

	badge := bentoTitleBadgeStyle.Render(" Tide ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(fmt.Sprintf(" 配置 %s 自定义模型", provider))
	s.WriteString(fmt.Sprintf("%s %s\n\n", badge, title))

	s.WriteString(fmt.Sprintf("请输入自定义模型名称（直接按 Enter 使用当前值: %s）：\n\n", m.currentModel))
	s.WriteString("  " + m.modelInput.View() + "\n\n")

	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(30, cardWidth-8)))
	s.WriteString(divider + "\n")

	footer := fmt.Sprintf("%s 保存配置并进入对话  %s 返回规格列表  %s 退出",
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

// handleModelCommand 集中处理模型配置相关的快捷指令（呼出向导看板或快速切换模型）
func (m Model) handleModelCommand(arg string) (Model, tea.Cmd) {
	m.chatInput.Reset()

	// 1. 无参数：直接呼出全屏平台选择看板
	if strings.TrimSpace(arg) == "" {
		m.state = stateSelectModel
		cfgView := m.agent.Config()
		m.syncActiveProvider(cfgView.Provider)
		m.cursor = m.selected
		return m, nil
	}

	// 2. 尝试匹配平台名称或别名 (基于协议契约 ID 与 Aliases 单源匹配)
	pKey := strings.ToLower(strings.TrimSpace(arg))
	cfgView := m.agent.Config()
	var targetProvider *protocol.ProviderInfo
	for i := range cfgView.Providers {
		p := &cfgView.Providers[i]
		if strings.EqualFold(p.ID, pKey) {
			targetProvider = p
			break
		}
		for _, alias := range p.Aliases {
			if strings.EqualFold(alias, pKey) {
				targetProvider = p
				break
			}
		}
		if targetProvider != nil {
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
				m.appendLocalProviderNotice(newView.Provider)
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
		m.appendLocalProviderNotice(newView.Provider)
	}

	if m.viewportReady {
		m.viewport.SetContent(m.renderChatMessages())
		m.viewport.GotoBottom()
	}
	return m, nil
}
