package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// openTraceInspector 呼出全量执行链路与 JSON 追踪看板
func (m Model) openTraceInspector() Model {
	m.traceEvents = m.agent.Traces()
	m.traceCursor = 0
	m.traceFocusRight = false

	cardWidth := max(60, min(m.width-4, 120))
	cardHeight := max(12, min(m.height-4, 36))
	leftWidth := max(26, min(36, cardWidth*32/100))
	rightWidth := max(32, cardWidth-leftWidth-4)
	vpHeight := max(6, cardHeight-6)

	m.traceViewport = viewport.New(rightWidth, vpHeight)
	if len(m.traceEvents) > 0 {
		m.traceViewport.SetContent(m.traceEvents[0].PrettyJSON())
	} else {
		m.traceViewport.SetContent("{\n  \"message\": \"当前暂无执行记录。发送任意问题后即可在此查看完整的全量 JSON 链路。\"\n}")
	}
	m.traceViewport.GotoTop()

	m.state = stateTraceInspector
	return m
}

// updateTraceInspector 处理追踪看板的按键交互
func (m Model) updateTraceInspector(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyEsc:
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil

		case tea.KeyTab:
			m.traceFocusRight = !m.traceFocusRight
			return m, nil
		}

		if !m.traceFocusRight {
			// 焦点在左侧事件列表
			switch msg.String() {
			case "q":
				m.state = stateChat
				m.chatInput.Focus()
				return m, nil

			case "up", "k":
				if m.traceCursor > 0 {
					m.traceCursor--
					if m.traceCursor < len(m.traceEvents) {
						m.traceViewport.SetContent(m.traceEvents[m.traceCursor].PrettyJSON())
						m.traceViewport.GotoTop()
					}
				}
				return m, nil

			case "down", "j":
				if m.traceCursor < len(m.traceEvents)-1 {
					m.traceCursor++
					if m.traceCursor < len(m.traceEvents) {
						m.traceViewport.SetContent(m.traceEvents[m.traceCursor].PrettyJSON())
						m.traceViewport.GotoTop()
					}
				}
				return m, nil

			case "enter", "right", "l":
				m.traceFocusRight = true
				return m, nil
			}
		} else {
			// 焦点在右侧 JSON 视口
			switch msg.String() {
			case "q":
				m.state = stateChat
				m.chatInput.Focus()
				return m, nil

			case "left", "h":
				m.traceFocusRight = false
				return m, nil
			}

			var cmd tea.Cmd
			m.traceViewport, cmd = m.traceViewport.Update(msg)
			return m, cmd
		}

	case tea.MouseMsg:
		var cmd tea.Cmd
		m.traceViewport, cmd = m.traceViewport.Update(msg)
		return m, cmd
	}

	return m, nil
}

// viewTraceInspector 渲染双栏 Master-Detail 结构化 JSON 追踪看板
func (m Model) viewTraceInspector() string {
	cardWidth := max(60, min(m.width-4, 120))
	cardHeight := max(12, min(m.height-4, 36))
	leftWidth := max(26, min(36, cardWidth*32/100))
	rightWidth := max(32, cardWidth-leftWidth-4)
	vpHeight := max(6, cardHeight-6)

	m.traceViewport.Width = rightWidth
	m.traceViewport.Height = vpHeight

	var sb strings.Builder

	// 1. 顶部 Header 状态信息
	badge := bentoTitleBadgeStyle.Render(" coustea ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(" 全系统执行链路与详细 JSON 追踪看板")
	sub := dimStyle.Render(fmt.Sprintf("当前轮次捕获事件: %d 个 (按 Tab 切换左右栏焦点，可在右侧视口翻页完整 JSON)", len(m.traceEvents)))
	sb.WriteString(fmt.Sprintf("%s %s\n%s\n\n", badge, title, sub))

	// 2. 左栏：事件时序列表
	var leftSB strings.Builder
	leftHeader := lipgloss.NewStyle().Bold(true).Foreground(colorOrange).Render("📋 事件时序流")
	leftSB.WriteString(leftHeader + "\n\n")

	if len(m.traceEvents) == 0 {
		leftSB.WriteString(dimStyle.Render("暂无事件记录\n"))
	} else {
		for i, ev := range m.traceEvents {
			cursor := "  "
			if m.traceCursor == i {
				cursor = cursorStyle.Render("▶ ")
			}

			titleText := ev.Title
			maxTitleLen := leftWidth - 6
			if maxTitleLen > 6 && len([]rune(titleText)) > maxTitleLen {
				titleText = string([]rune(titleText)[:maxTitleLen-3]) + "..."
			}

			var line string
			if m.traceCursor == i {
				if !m.traceFocusRight {
					line = lipgloss.NewStyle().Bold(true).Foreground(colorBrandLight).Render(titleText)
				} else {
					line = lipgloss.NewStyle().Bold(true).Foreground(colorCyan).Render(titleText)
				}
			} else {
				line = dimStyle.Render(titleText)
			}
			leftSB.WriteString(fmt.Sprintf("%s%s\n", cursor, line))
		}
	}

	leftBorderColor := colorBorder
	if !m.traceFocusRight {
		leftBorderColor = colorBrand
	}
	leftBox := lipgloss.NewStyle().
		Width(leftWidth).
		Height(vpHeight+2).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(leftBorderColor).
		Background(colorSurface).
		Padding(0, 1).
		Render(leftSB.String())

	// 3. 右栏：全量 JSON 视口
	var rightSB strings.Builder
	selectedTitle := "详细 JSON 报文"
	if m.traceCursor >= 0 && m.traceCursor < len(m.traceEvents) {
		selectedTitle = m.traceEvents[m.traceCursor].Title
	}
	rightHeader := lipgloss.NewStyle().Bold(true).Foreground(colorCyan).Render("📦 " + selectedTitle)
	scrollPercent := int(m.traceViewport.ScrollPercent() * 100)
	rightHint := dimStyle.Render(fmt.Sprintf(" [已滚至 %d%%]", scrollPercent))
	rightSB.WriteString(rightHeader + rightHint + "\n")
	rightSB.WriteString(m.traceViewport.View())

	rightBorderColor := colorBorder
	if m.traceFocusRight {
		rightBorderColor = colorBrand
	}
	rightBox := lipgloss.NewStyle().
		Width(rightWidth).
		Height(vpHeight+2).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(rightBorderColor).
		Background(colorSurface).
		Padding(0, 1).
		Render(rightSB.String())

	// 4. 左右拼接
	mainArea := lipgloss.JoinHorizontal(lipgloss.Top, leftBox, " ", rightBox)
	sb.WriteString(mainArea + "\n\n")

	// 5. 底部操作说明
	divider := lipgloss.NewStyle().Foreground(colorBorder).Render(strings.Repeat("─", max(30, cardWidth-8)))
	sb.WriteString(divider + "\n")

	focusHint := "当前焦点: 左栏事件流"
	if m.traceFocusRight {
		focusHint = "当前焦点: 右栏 JSON 视口 (可用 ↑/↓/PgUp/PgDn 滚动)"
	}
	footer := fmt.Sprintf("%s  %s 切换事件  %s 切换左右焦点  %s 滚动全文  %s 返回对话",
		lipgloss.NewStyle().Foreground(colorYellow).Render(focusHint),
		keycapPillStyle.Render("[↑/↓, k/j]"),
		keycapPillStyle.Render("[Tab]"),
		keycapPillStyle.Render("[PgUp/PgDn]"),
		keycapPillStyle.Render("[Esc/q]"),
	)
	sb.WriteString(footerStyle.Render(footer))

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorBorderActive).
		Background(colorSurface).
		Padding(1, 2).
		Width(cardWidth).
		Render(sb.String()) + "\n"
}
