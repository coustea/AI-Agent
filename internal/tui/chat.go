package tui

import (
	"context"
	"fmt"
	"strings"

	"my-agent/internal/protocol"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ToolCallRecord 结构化记录单次工具调用过程与结果
type ToolCallRecord struct {
	protocol.ToolCall
	Result  string `json:"result,omitempty"`
	IsError bool   `json:"is_error,omitempty"`
	Running bool   `json:"running,omitempty"`
}

// ChatMessage 用于在界面上展示发送和接收的消息
type ChatMessage struct {
	Sender           string           // "You", "coustea", "System"
	Content          string           // 最终回复文本
	ReasoningContent string           // 深度思考链 (DeepSeek 等)
	ToolCalls        []ToolCallRecord // 结构化工具调用列表
	Usage            *protocol.Usage  // 携带的 Token 用量统计（可选）
}

// updateChat 处理聊天页面的键盘输入和发送逻辑
func (m Model) updateChat(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		// 1. 若当前存在挂起的权限审批请求，优先处理审批交互
		if m.pendingPerm != nil {
			reqID := m.pendingPerm.RequestID
			switch msg.String() {
			case "y", "Y":
				_ = m.agent.RespondPermission(reqID, protocol.DecisionAllowOnce)
				m.pendingPerm = nil
				m.chatInput.Placeholder = "coustea 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			case "a", "A":
				_ = m.agent.RespondPermission(reqID, protocol.DecisionAllowSession)
				m.pendingPerm = nil
				m.chatInput.Placeholder = "coustea 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			case "n", "N":
				_ = m.agent.RespondPermission(reqID, protocol.DecisionDeny)
				m.pendingPerm = nil
				m.chatInput.Placeholder = "coustea 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}

			if msg.Type == tea.KeyEsc {
				_ = m.agent.RespondPermission(reqID, protocol.DecisionDeny)
				m.pendingPerm = nil
				m.chatInput.Placeholder = "coustea 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}

			// 处于权限审批等待状态时，屏蔽其他输入
			return m, nil
		}

		// 2. 翻页与视口滚动快捷键支持 (PgUp, PgDown)
		switch msg.Type {
		case tea.KeyPgUp, tea.KeyPgDown:
			if m.viewportReady {
				var cmd tea.Cmd
				m.viewport, cmd = m.viewport.Update(msg)
				return m, cmd
			}

		case tea.KeyEnter:
			// 如果正在流式生成中，避免重复触发
			if m.isGenerating {
				return m, nil
			}

			text := strings.TrimSpace(m.chatInput.Value())
			if text == "" {
				return m, nil
			}

			// 拦截并分发快捷指令（委托给 command.go / model.go 处理，chat.go 纯粹负责聊天设计与交互）
			if newM, cmd, handled := m.handleSlashCommand(text); handled {
				return newM, cmd
			}

			// 发送消息展示：将用户输入添加到消息历史
			m.messages = append(m.messages, ChatMessage{
				Sender:  "You",
				Content: text,
			})
			m.chatInput.Reset()

			// 预备一条 Assistant 消息占位，等待流式增量填入
			m.messages = append(m.messages, ChatMessage{
				Sender:  "coustea",
				Content: "",
			})
			m.isGenerating = true
			m.chatInput.Placeholder = "coustea 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"

			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}

			// 未就绪校验：远程厂商缺密钥时先引导配置（本地服务恒就绪）
			if !m.agent.Config().HasAPIKey {
				m.messages[len(m.messages)-1].Content = "[未配置可用模型] 请先输入 /model 配置 API Key 或设置环境变量 (DEEPSEEK_API_KEY / GEMINI_API_KEY)。"
				m.isGenerating = false
				m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}

			ctx, cancel := context.WithCancel(context.Background())
			m.cancel = cancel
			ch, err := m.agent.StreamRun(ctx, text)
			if err != nil {
				m.cancel = nil
				m.messages[len(m.messages)-1].Content = fmt.Sprintf("[请求失败: %v]", err)
				m.isGenerating = false
				m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}
			return m, waitForAgentEvent(ch)
		}
	}

	var cmd tea.Cmd
	m.chatInput, cmd = m.chatInput.Update(msg)
	return m, cmd
}

// renderHeaderBar 渲染固定在顶部的 Claude 风格品牌与状态栏
func (m Model) renderHeaderBar() string {
	var sb strings.Builder

	cfg := m.agent.Config()
	modelInfo := "未配置模型 (输入 /model 配置)"
	if cfg.ModelName != "" {
		modelInfo = fmt.Sprintf("%s • %s", cfg.Provider, cfg.ModelName)
	}

	brandBadge := headerBadgeStyle.Render(" coustea ")
	modelTag := headerTagStyle.Render("● " + modelInfo)

	// 计算长效记忆激活篇数
	memCount := m.agent.MemoryCount()
	memTag := headerMemoryStyle.Render(fmt.Sprintf("🧠 %d 篇记忆生效", memCount))

	dirTag := headerDirStyle.Render(" 📂 目录: " + m.agent.WorkDir())

	headerRow := fmt.Sprintf("%s %s %s%s", brandBadge, modelTag, memTag, dirTag)
	sb.WriteString("\n" + headerRow + "\n")

	divider := headerDividerStyle.Render(strings.Repeat("─", max(50, m.width-2)))
	sb.WriteString(divider)
	return sb.String()
}

// renderStatusBar 渲染运行状态指示器 (Spinner + 就绪/思考/工具中 + 视口滚动百分比)
func (m Model) renderStatusBar() string {
	var statusText string
	if m.pendingPerm != nil {
		statusText = permissionWarnStyle.Render("🛡️ 等待授权决策 (Gate 3)")
	} else if m.activeToolName != "" {
		statusText = toolRunningStyle.Render(fmt.Sprintf("%s 正在调用 [%s]...", m.spinner.View(), m.activeToolName))
	} else if m.isGenerating {
		statusText = statusThinkingStyle.Render(fmt.Sprintf("%s 正在深度思考生成中...", m.spinner.View()))
	} else {
		statusText = statusReadyStyle.Render("● 就绪")
	}

	scrollHint := ""
	if m.viewportReady && m.viewport.TotalLineCount() > m.viewport.Height {
		percent := int(m.viewport.ScrollPercent() * 100)
		scrollHint = scrollIndicatorStyle.Render(fmt.Sprintf(" [已滚至 %d%% | PgUp/PgDn 翻页]", percent))
	}

	return fmt.Sprintf(" %s%s\n", statusText, scrollHint)
}

// renderPermissionCard 渲染 Claude Code 风格高安全性 Gate 3 权限审批交互卡片
func (m Model) renderPermissionCard() string {
	if m.pendingPerm == nil {
		return ""
	}
	cardWidth := max(60, m.width-6)
	req := m.pendingPerm

	var sb strings.Builder
	title := lipgloss.NewStyle().Bold(true).Foreground(colorYellow).Render("🛡️  [权限审批 Gate 3] · 拦截潜在高危行为")
	sb.WriteString(title + "\n\n")

	sb.WriteString(fmt.Sprintf("  %s %s\n", lipgloss.NewStyle().Bold(true).Foreground(colorOrange).Render("⚡ 工具目标:"), req.ToolName))
	argPreview := lipgloss.NewStyle().Background(colorSurface).Foreground(colorCyan).Padding(0, 1).Render(req.Arguments)
	sb.WriteString(fmt.Sprintf("  %s %s\n", lipgloss.NewStyle().Bold(true).Foreground(colorCyan).Render("📝 风险调用:"), argPreview))
	sb.WriteString(fmt.Sprintf("  %s %s\n", lipgloss.NewStyle().Bold(true).Foreground(colorRed).Render("⚠️  拦截原因:"), req.Reason))

	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(20, cardWidth-6)))
	sb.WriteString("\n" + divider + "\n")

	actions := fmt.Sprintf("  %s %s   %s %s   %s %s",
		keycapAllowStyle.Render("[y] 允许本次"),
		dimStyle.Render("(单次放行)"),
		keycapSessionStyle.Render("[a] 本会话始终允许"),
		dimStyle.Render("(信任同类)"),
		keycapDenyStyle.Render("[n/Esc] 阻断执行"),
		dimStyle.Render("(安全拦截)"),
	)
	sb.WriteString(actions)

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorYellow).
		Background(colorYellowSubtle).
		Padding(0, 1).
		Width(cardWidth).
		Render(sb.String())
}

// renderInputBox 渲染高视觉重心的 Command Dock 交互控制台驾驶舱
func (m Model) renderInputBox() string {
	cardWidth := max(60, m.width-6)

	var borderCol lipgloss.Color = colorBrand
	var statusBadge string

	if m.pendingPerm != nil {
		borderCol = colorYellow
		statusBadge = dockPermissionBadgeStyle.Render(" 🛡️ 权限审批决策中 ")
	} else if m.isGenerating {
		borderCol = colorYellow
		statusBadge = dockGeneratingBadgeStyle.Render(" ⏳ 思考生成中 ")
	} else {
		statusBadge = dockPromptBadgeStyle.Render(" 💬 PROMPT · 对话模式 ")
	}

	cfg := m.agent.Config()
	modelBadge := ""
	if cfg.ModelName != "" {
		modelBadge = dockModelTagStyle.Render(fmt.Sprintf("● %s • %s", cfg.Provider, cfg.ModelName))
	}

	topRow := fmt.Sprintf("%s  %s", statusBadge, modelBadge)
	inputRow := m.chatInput.View()

	// 底部操作快捷键栏
	var footerRow string
	if m.pendingPerm != nil {
		footerRow = fmt.Sprintf(" %s %s   %s %s   %s %s",
			keycapAllowStyle.Render("[y] 允许本次"),
			dimStyle.Render("(单次放行)"),
			keycapSessionStyle.Render("[a] 本会话始终信任"),
			dimStyle.Render("(信任同类)"),
			keycapDenyStyle.Render("[n/Esc] 阻断执行"),
			dimStyle.Render("(安全拦截)"),
		)
	} else {
		sep := dimStyle.Render("  •  ")
		item := func(key, desc string) string {
			return fmt.Sprintf("%s %s", keycapPillStyle.Render(key), dimStyle.Render(desc))
		}
		footerRow = fmt.Sprintf(" %s%s%s%s%s%s%s%s%s",
			item("Enter", "发送"),
			sep,
			item("PgUp/PgDn", "翻页"),
			sep,
			item("/model", "切换模型"),
			sep,
			item("/clear", "清屏"),
			sep,
			item("Ctrl+C", "退出"),
		)
	}

	divider := dockDividerStyle.Render(strings.Repeat("─", max(20, cardWidth-4)))
	dockContent := fmt.Sprintf("%s\n\n  %s\n\n%s\n%s", topRow, inputRow, divider, footerRow)

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderCol).
		Background(colorSurface).
		Padding(0, 1).
		Width(cardWidth).
		Render(dockContent)
}

// renderFooterBar 渲染底部快捷键提示胶囊（已集成于 Command Dock 中）
func (m Model) renderFooterBar() string {
	if m.pendingPerm != nil {
		return permissionWarnStyle.Render("等待权限决策: [y] 允许单次  [a] 会话始终允许  [n/Esc] 阻断执行  [Ctrl+C] 退出")
	}

	sep := dimStyle.Render("  ")
	item := func(key, desc string) string {
		return fmt.Sprintf("%s %s", keycapPillStyle.Render(key), dimStyle.Render(desc))
	}

	return fmt.Sprintf(" %s%s%s%s%s%s%s%s%s\n",
		item("Enter", "发送"),
		sep,
		item("PgUp/PgDn", "翻页滚动"),
		sep,
		item("/model", "切换模型"),
		sep,
		item("/clear", "清屏"),
		sep,
		item("Ctrl+C", "退出"),
	)
}

// renderChatMessages 将所有历史消息格式化为适用于 Viewport 渲染的高质量通透呼吸文本 (无生硬封闭边框)
func (m Model) renderChatMessages() string {
	cardWidth := max(60, m.width-6)
	if len(m.messages) == 0 {
		title := lipgloss.NewStyle().Bold(true).Foreground(colorBrand).Render("👋 欢迎使用 coustea 智能助手")
		text := "  在下方输入框键入问题并按 Enter 即可开始多轮深度对话。\n" +
			"  随时输入 /model 调出模型配置向导，输入 /clear 可清空上下文记忆。"
		return fmt.Sprintf("\n%s\n%s\n\n", title, dimStyle.Render(text))
	}

	var sb strings.Builder
	for i, msg := range m.messages {
		switch msg.Sender {
		case "You":
			badge := userBadgeStyle.Render(" 👤 You ")
			lines := strings.Split(msg.Content, "\n")
			var indented strings.Builder
			for j, line := range lines {
				if j > 0 {
					indented.WriteString("\n")
				}
				indented.WriteString("  " + userPromptTextStyle.Render(line))
			}
			sb.WriteString(fmt.Sprintf("%s\n%s\n\n", badge, indented.String()))

		case "System":
			badge := systemBadgeStyle.Render(" ℹ System ")
			lines := strings.Split(msg.Content, "\n")
			var indented strings.Builder
			for j, line := range lines {
				if j > 0 {
					indented.WriteString("\n")
				}
				indented.WriteString("  " + dimStyle.Render(line))
			}
			sb.WriteString(fmt.Sprintf("%s\n%s\n\n", badge, indented.String()))

		case "coustea":
			// 1. 若有深度思考链，独立优雅呈现
			if msg.ReasoningContent != "" {
				thoughtHeader := reasoningTitleStyle.Render("💭 思考过程 (Thinking Process):")
				thoughtText := reasoningTextStyle.Render(msg.ReasoningContent)
				sb.WriteString(fmt.Sprintf("  %s\n  %s\n\n", thoughtHeader, thoughtText))
			}

			// 2. 若有工具调用，彩色紧凑结构化呈现
			for _, tc := range msg.ToolCalls {
				var header string
				if tc.Running {
					header = toolRunningStyle.Render("⚙️  正在执行工具: ") + toolHeaderStyle.Render(tc.Name)
				} else if tc.IsError {
					header = toolResultErrorStyle.Render("✖  工具执行报错: ") + toolHeaderStyle.Render(tc.Name)
				} else {
					header = toolResultSuccessStyle.Render("✔  工具执行完成: ") + toolHeaderStyle.Render(tc.Name)
				}

				var body strings.Builder
				body.WriteString(fmt.Sprintf("  %s\n", header))

				if tc.Arguments != "" && tc.Arguments != "{}" {
					body.WriteString(fmt.Sprintf("    ↳ %s\n", toolSnippetStyle.Render("参数: "+tc.Arguments)))
				}
				if tc.Result != "" {
					snippet := strings.TrimSpace(tc.Result)
					lines := strings.Split(snippet, "\n")
					if len(lines) > 4 {
						snippet = strings.Join(lines[:4], "\n") + fmt.Sprintf("\n    ... (共 %d 行，其余已折叠)", len(lines))
					} else if len(snippet) > 240 {
						snippet = snippet[:240] + "... (已截断)"
					}
					body.WriteString(fmt.Sprintf("    ↳ %s\n", toolSnippetStyle.Render("结果: ")+snippet))
				}
				sb.WriteString(body.String() + "\n")
			}

			// 3. 回复正文：完全释放 Markdown 富文本能力，通透自然排版
			if msg.Content != "" || (m.isGenerating && i == len(m.messages)-1 && len(msg.ToolCalls) == 0 && msg.ReasoningContent == "") {
				header := assistantBadgeStyle.Render(" 🤖 coustea ")
				var bodyText string
				if msg.Content != "" {
					if m.isGenerating && i == len(m.messages)-1 {
						bodyText = msg.Content + lipgloss.NewStyle().Foreground(colorBrand).Render(" ▊")
					} else {
						bodyText = renderMarkdown(msg.Content, cardWidth)
					}
				} else {
					bodyText = m.spinner.View() + dimStyle.Render(" 正在思考中...")
				}

				usageText := ""
				if msg.Usage != nil && msg.Usage.TotalTokens > 0 {
					usageText = "\n  " + tokenBadgeStyle.Render(fmt.Sprintf("📊 Token 用量: %d (输入 %d / 输出 %d)",
						msg.Usage.TotalTokens, msg.Usage.PromptTokens, msg.Usage.CompletionTokens))
				}

				sb.WriteString(fmt.Sprintf("%s\n%s%s\n\n", header, bodyText, usageText))
			}

		default:
			sb.WriteString(fmt.Sprintf("%s: %s\n\n", msg.Sender, msg.Content))
		}
	}

	return sb.String()
}

// viewChat 渲染 Claude Code 风格的主聊天页面
func (m Model) viewChat() string {
	var s strings.Builder

	// 1. 顶部固定 Header 状态栏
	s.WriteString(m.renderHeaderBar() + "\n\n")

	// 2. 中部 Viewport 聊天记录滚动展示
	if m.viewportReady {
		s.WriteString(m.viewport.View() + "\n\n")
	} else {
		s.WriteString(m.renderChatMessages() + "\n\n")
	}

	// 3. 运行状态栏 (Spinner / 就绪 / 视口滚动百分比)
	s.WriteString(m.renderStatusBar())

	// 4. 若有挂起的权限审批，高亮呈现权限提示卡片
	if m.pendingPerm != nil {
		s.WriteString(m.renderPermissionCard() + "\n\n")
	}

	// 5. 底部高亮交互驾驶舱 (Command Dock: 整合输入框、模式状态、当前模型与按键操作)
	s.WriteString(m.renderInputBox() + "\n")

	return s.String()
}
