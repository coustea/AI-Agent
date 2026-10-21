package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ReasoningEntry 描述一个独立的思考过程单元
type ReasoningEntry struct {
	TurnIndex    int    // 属于第几轮对话 (1-indexed)
	StepIndex    int    // 属于该轮第几个思考阶段 (1-indexed)
	Prompt       string // 触发该思考的用户问题提问摘要
	Content      string // 思考链完整文本
	CharCount    int    // 字符数
	IsGenerating bool   // 是否正在实时生成中
}

// collectReasoningEntries 从消息历史中解析提取所有思考阶段
func collectReasoningEntries(messages []ChatMessage, isGenerating bool) []ReasoningEntry {
	var entries []ReasoningEntry
	lastPrompt := ""
	turn := 0

	for msgIdx, msg := range messages {
		if msg.Sender == "You" {
			turn++
			lastPrompt = strings.TrimSpace(msg.Content)
			if len([]rune(lastPrompt)) > 32 {
				lastPrompt = string([]rune(lastPrompt)[:32]) + "..."
			}
		} else if msg.Sender == "Tide" {
			step := 0
			isLastMsg := msgIdx == len(messages)-1
			for bIdx, b := range msg.Blocks {
				if b.Kind == BlockReasoning && strings.TrimSpace(b.Text) != "" {
					step++
					isLastBlock := bIdx == len(msg.Blocks)-1
					promptText := lastPrompt
					if promptText == "" {
						promptText = fmt.Sprintf("轮次 %d 问答", turn)
					}
					entries = append(entries, ReasoningEntry{
						TurnIndex:    turn,
						StepIndex:    step,
						Prompt:       promptText,
						Content:      b.Text,
						CharCount:    len([]rune(b.Text)),
						IsGenerating: isGenerating && isLastMsg && isLastBlock,
					})
				}
			}
		}
	}
	return entries
}

// openThinkingViewer 呼出全屏沉浸式思考过程看板
func (m Model) openThinkingViewer() Model {
	m.thinkingEntries = collectReasoningEntries(m.messages, m.isGenerating)
	m.thinkingRawMode = false
	m.thinkingFocusText = true

	// 默认定位到最新的思考过程
	if len(m.thinkingEntries) > 0 {
		m.thinkingCursor = len(m.thinkingEntries) - 1
	} else {
		m.thinkingCursor = 0
	}

	cardWidth := max(70, min(m.width-2, 120))
	cardHeight := max(16, min(m.height-2, 38))
	boxWidth := cardWidth - 6
	vpWidth := max(30, boxWidth-2)
	vpHeight := max(6, cardHeight-11)

	m.thinkingViewport = viewport.New(vpWidth, vpHeight)
	if len(m.thinkingEntries) > 0 {
		m.thinkingViewport.SetContent(m.renderThinkingContent(m.thinkingEntries[m.thinkingCursor], vpWidth))
	} else {
		m.thinkingViewport.SetContent(m.renderThinkingEmptyNotice(vpWidth))
	}
	m.thinkingViewport.GotoTop()

	m.state = stateThinkingViewer
	return m
}

// syncThinkingViewerContent 同步更新看板视口中的最新思考内容（在流式思考生成中自动响应）
func (m *Model) syncThinkingViewerContent() {
	oldLen := len(m.thinkingEntries)
	m.thinkingEntries = collectReasoningEntries(m.messages, m.isGenerating)
	if len(m.thinkingEntries) == 0 {
		return
	}

	// 若光标原本在最新一项（或超出范围），自动跟进到最新阶段
	if m.thinkingCursor == oldLen-1 || m.thinkingCursor >= len(m.thinkingEntries) {
		m.thinkingCursor = len(m.thinkingEntries) - 1
	}

	if m.thinkingCursor == len(m.thinkingEntries)-1 {
		cardWidth := max(70, min(m.width-2, 120))
		boxWidth := cardWidth - 6
		vpWidth := max(30, boxWidth-2)

		atBottom := m.thinkingViewport.AtBottom()
		m.thinkingViewport.SetContent(m.renderThinkingContent(m.thinkingEntries[m.thinkingCursor], vpWidth))
		if atBottom {
			m.thinkingViewport.GotoBottom()
		}
	}
}

// updateThinkingViewer 处理思考过程沉浸看板的按键与翻页交互
func (m Model) updateThinkingViewer(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		// 1. 返回主聊天页面
		switch msg.Type {
		case tea.KeyEsc:
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil
		}

		if msg.String() == "q" {
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil
		}

		// 2. 切换 Markdown 富文本与纯文本 Raw 模式
		if msg.String() == "r" || msg.String() == "R" {
			m.thinkingRawMode = !m.thinkingRawMode
			if len(m.thinkingEntries) > 0 && m.thinkingCursor >= 0 && m.thinkingCursor < len(m.thinkingEntries) {
				cardWidth := max(70, min(m.width-2, 120))
				boxWidth := cardWidth - 6
				vpWidth := max(30, boxWidth-2)
				m.thinkingViewport.SetContent(m.renderThinkingContent(m.thinkingEntries[m.thinkingCursor], vpWidth))
			}
			return m, nil
		}

		// 3. 多阶段/多轮次思考切换 (Left/Right, h/l, [, ])
		switch msg.String() {
		case "left", "h", "[":
			if m.thinkingCursor > 0 {
				m.thinkingCursor--
				cardWidth := max(70, min(m.width-2, 120))
				boxWidth := cardWidth - 6
				vpWidth := max(30, boxWidth-2)
				m.thinkingViewport.SetContent(m.renderThinkingContent(m.thinkingEntries[m.thinkingCursor], vpWidth))
				m.thinkingViewport.GotoTop()
			}
			return m, nil

		case "right", "l", "]":
			if m.thinkingCursor < len(m.thinkingEntries)-1 {
				m.thinkingCursor++
				cardWidth := max(70, min(m.width-2, 120))
				boxWidth := cardWidth - 6
				vpWidth := max(30, boxWidth-2)
				m.thinkingViewport.SetContent(m.renderThinkingContent(m.thinkingEntries[m.thinkingCursor], vpWidth))
				m.thinkingViewport.GotoTop()
			}
			return m, nil

		case "tab":
			if len(m.thinkingEntries) > 1 {
				m.thinkingCursor = (m.thinkingCursor + 1) % len(m.thinkingEntries)
				cardWidth := max(70, min(m.width-2, 120))
				boxWidth := cardWidth - 6
				vpWidth := max(30, boxWidth-2)
				m.thinkingViewport.SetContent(m.renderThinkingContent(m.thinkingEntries[m.thinkingCursor], vpWidth))
				m.thinkingViewport.GotoTop()
			}
			return m, nil
		}

		// 4. 视口滚动交由 viewport 处理
		var cmd tea.Cmd
		m.thinkingViewport, cmd = m.thinkingViewport.Update(msg)
		return m, cmd

	case tea.MouseMsg:
		var cmd tea.Cmd
		m.thinkingViewport, cmd = m.thinkingViewport.Update(msg)
		return m, cmd
	}

	return m, nil
}

// viewThinkingViewer 渲染全屏沉浸式思考过程看板
func (m Model) viewThinkingViewer() string {
	cardWidth := max(70, min(m.width-2, 120))
	cardHeight := max(16, min(m.height-2, 38))
	boxWidth := cardWidth - 6
	vpWidth := max(30, boxWidth-2)
	vpHeight := max(6, cardHeight-11)

	m.thinkingViewport.Width = vpWidth
	m.thinkingViewport.Height = vpHeight

	var sb strings.Builder

	// 1. 顶部 Header 状态信息
	badge := thinkingBadgeStyle.Render(" 🧠 深度思考过程看板 ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorReasoning).Render(" Thinking Process Inspector")

	cfg := m.agent.Config()
	modelTag := ""
	if cfg.ModelName != "" {
		modelTag = dockModelTagStyle.Render("● " + cfg.ModelName)
	}

	topRow := fmt.Sprintf("%s%s  %s", badge, title, modelTag)
	sb.WriteString(topRow + "\n\n")

	// 2. 思考轮次选择标签栏（当存在多个思考阶段时展示）
	if len(m.thinkingEntries) > 1 {
		var tabsRow strings.Builder
		for idx, entry := range m.thinkingEntries {
			tabLabel := fmt.Sprintf(" %d. 轮次%d·阶段%d (%s) ", idx+1, entry.TurnIndex, entry.StepIndex, entry.Prompt)
			if idx == m.thinkingCursor {
				tabsRow.WriteString(thinkingTabActiveStyle.Render(tabLabel) + " ")
			} else {
				tabsRow.WriteString(thinkingTabInactiveStyle.Render(tabLabel) + " ")
			}
		}
		sb.WriteString(tabsRow.String() + "\n\n")
	}

	// 3. 统计状态行
	if len(m.thinkingEntries) > 0 && m.thinkingCursor < len(m.thinkingEntries) {
		cur := m.thinkingEntries[m.thinkingCursor]
		var statusText string
		if cur.IsGenerating {
			statusText = dockGeneratingBadgeStyle.Render(" ⏳ 深度推理思考中... ")
		} else {
			statusText = statusReadyStyle.Render(" ✔ 思考已完成 ")
		}

		modeHint := "Markdown渲染 (按 r 查看纯文本)"
		if m.thinkingRawMode {
			modeHint = "原始纯文本 (按 r 查看Markdown)"
		}

		infoRow := fmt.Sprintf("%s %s", statusText, dimStyle.Render(fmt.Sprintf("• 共 %d 字符 (约 %d Tokens) • %s", cur.CharCount, cur.CharCount/3, modeHint)))
		sb.WriteString(infoRow + "\n\n")
	}

	// 4. 居中思考内容视口盒子
	viewportBox := thinkingCardStyle.
		Width(boxWidth).
		Height(vpHeight + 2).
		Render(m.thinkingViewport.View())
	sb.WriteString(viewportBox + "\n\n")

	// 5. 底部快捷键与滚动百分比栏
	scrollPercent := int(m.thinkingViewport.ScrollPercent() * 100)
	scrollTag := dimStyle.Render(fmt.Sprintf("[已滚至 %d%%]", scrollPercent))

	sep := dimStyle.Render("  •  ")
	item := func(key, desc string) string {
		return fmt.Sprintf("%s %s", keycapPillStyle.Render(key), dimStyle.Render(desc))
	}

	footerRow := fmt.Sprintf(" %s%s%s%s%s%s%s %s",
		item("Esc/q", "返回对话"),
		sep,
		item("PgUp/PgDn/↑↓", "滚动翻看"),
		sep,
		item("r", "切换模式"),
		sep,
		item("←/→/Tab", "切换轮次"),
		scrollTag,
	)
	sb.WriteString(footerRow)

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorReasoning).
		Background(colorSurface).
		Padding(1, 2).
		Width(cardWidth).
		Render(sb.String())
}

// renderThinkingContent 格式化思考内容
func (m Model) renderThinkingContent(entry ReasoningEntry, width int) string {
	content := strings.TrimSpace(entry.Content)
	if content == "" {
		return dimStyle.Render("（思考过程为空）")
	}

	if m.thinkingRawMode {
		return reasoningTextStyle.Render(content)
	}

	// 采用 Markdown 渲染并保持思考样式底色
	rendered := renderMarkdown(content, width)
	if rendered == "" {
		return content
	}
	return rendered
}

// renderThinkingEmptyNotice 提示无思考过程的空状态
func (m Model) renderThinkingEmptyNotice(width int) string {
	var sb strings.Builder
	sb.WriteString("\n")
	sb.WriteString("  " + reasoningTitleStyle.Render("💡 当前会话暂无思考过程记录") + "\n\n")
	sb.WriteString("  " + dimStyle.Render("当使用具备深度思考推理能力的大模型时：\n"))
	sb.WriteString("  " + dimStyle.Render("  • DeepSeek: deepseek-reasoner (R1)\n"))
	sb.WriteString("  " + dimStyle.Render("  • 讯飞星辰: spark-x2.5 (官方主力免费体验模型，带深度推理)\n"))
	sb.WriteString("  " + dimStyle.Render("  • Gemini: gemini-2.5-flash / gemini-2.5-pro\n\n"))
	sb.WriteString("  " + dimStyle.Render("模型在生成最终回答前输出的思考推导过程将自动记录在此，\n"))
	sb.WriteString("  " + dimStyle.Render("随时按 Ctrl+T 或输入 /think 即可呼出本看板沉浸查阅。"))
	return sb.String()
}
