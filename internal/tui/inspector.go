package tui

import (
	"encoding/json"
	"fmt"
	"strings"

	"my-agent/internal/protocol"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// cleanTracePayload 对底层 Payload 提取真实动态数据，剔除每轮重复的静态无用噪声
func cleanTracePayload(ev protocol.TraceEvent) any {
	m, ok := ev.Payload.(map[string]any)
	if !ok || ev.Type != "llm_req" {
		// 其余事件 (llm_resp, tool_start, tool_end, turn_start, turn_end)
		// 本身全都是关键的动态执行数据，100% 保留原始对象
		return ev.Payload
	}

	// 仅针对 llm_req 进行脱水：剥离巨型系统提示词与上百行的静态 tools schema
	clean := make(map[string]any, len(m))
	for k, v := range m {
		clean[k] = v
	}

	// 1. 将千字重复系统提示词压缩为紧凑的说明摘要
	if sys, ok := m["system_prompt"].(string); ok && sys != "" {
		clean["system_prompt"] = fmt.Sprintf("[已注入系统提示词, 共 %d 字符 (按 r 查看全量)]", len([]rune(sys)))
	}

	// 2. 将静态工具参数 Schema 压缩为精炼的工具名称列表
	if tools, ok := m["tools"].([]protocol.ToolDefinition); ok {
		names := make([]string, 0, len(tools))
		for _, t := range tools {
			names = append(names, t.Name)
		}
		clean["tools_available"] = names
		delete(clean, "tools")
	} else if toolsAny, ok := m["tools"].([]any); ok {
		names := make([]string, 0, len(toolsAny))
		for _, t := range toolsAny {
			if tm, ok := t.(map[string]any); ok {
				if n, ok := tm["name"].(string); ok {
					names = append(names, n)
				}
			}
		}
		clean["tools_available"] = names
		delete(clean, "tools")
	}

	// 3. 针对 messages 消息历史：若历史过多，突出保留本步输入
	if msgs, ok := m["messages"].([]protocol.Message); ok && len(msgs) > 2 {
		clean["_history_summary"] = fmt.Sprintf("历史消息共 %d 条，以下展示最近输入", len(msgs))
		clean["messages"] = msgs[len(msgs)-2:]
	}

	return clean
}

// formatTraceJSON 依据当前模式格式化 JSON 字符串
func formatTraceJSON(ev protocol.TraceEvent, raw bool) string {
	payload := ev.Payload
	if !raw {
		payload = cleanTracePayload(ev)
	}
	b, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return fmt.Sprintf("{\n  \"error\": %q\n}", err.Error())
	}
	return string(b)
}

// openTraceInspector 呼出上下折叠结构的执行链路与底层 JSON 追踪看板
func (m Model) openTraceInspector() Model {
	m.traceEvents = m.agent.Traces()
	m.traceCursor = 0
	m.traceFocusJSON = false
	m.traceRawMode = false

	cardWidth := max(70, min(m.width-2, 120))
	cardHeight := max(16, min(m.height-2, 38))
	boxWidth := cardWidth - 6
	vpWidth := max(30, boxWidth-2)
	vpHeight := max(6, cardHeight-15)

	m.traceViewport = viewport.New(vpWidth, vpHeight)
	if len(m.traceEvents) > 0 {
		m.traceViewport.SetContent(formatTraceJSON(m.traceEvents[0], m.traceRawMode))
	} else {
		m.traceViewport.SetContent("{\n  \"message\": \"当前暂无执行记录。发送任意问题后即可在此查看完整的全量底层 JSON。\"\n}")
	}
	m.traceViewport.GotoTop()

	m.state = stateTraceInspector
	return m
}

// updateTraceInspector 处理上下折叠看板的按键交互
func (m Model) updateTraceInspector(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		// 1. 全局退出快捷键
		switch msg.Type {
		case tea.KeyEsc:
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil
		case tea.KeyTab:
			m.traceFocusJSON = !m.traceFocusJSON
			return m, nil
		}

		if msg.String() == "q" {
			m.state = stateChat
			m.chatInput.Focus()
			return m, nil
		}

		// 2. 按 'r' 键在 Clean JSON 与 Raw JSON 之间一键切换
		if msg.String() == "r" || msg.String() == "R" {
			m.traceRawMode = !m.traceRawMode
			if len(m.traceEvents) > 0 && m.traceCursor >= 0 && m.traceCursor < len(m.traceEvents) {
				m.traceViewport.SetContent(formatTraceJSON(m.traceEvents[m.traceCursor], m.traceRawMode))
			}
			return m, nil
		}

		// 3. 上层步骤栏聚焦交互
		if !m.traceFocusJSON {
			switch msg.String() {
			case "up", "k":
				if m.traceCursor > 0 {
					m.traceCursor--
					if m.traceCursor < len(m.traceEvents) {
						m.traceViewport.SetContent(formatTraceJSON(m.traceEvents[m.traceCursor], m.traceRawMode))
						m.traceViewport.GotoTop()
					}
				}
				return m, nil

			case "down", "j":
				if m.traceCursor < len(m.traceEvents)-1 {
					m.traceCursor++
					if m.traceCursor < len(m.traceEvents) {
						m.traceViewport.SetContent(formatTraceJSON(m.traceEvents[m.traceCursor], m.traceRawMode))
						m.traceViewport.GotoTop()
					}
				}
				return m, nil

			case "enter":
				// 回车键进入下方全宽 JSON 视口
				m.traceFocusJSON = true
				return m, nil
			}
		} else {
			// 4. 下层全宽 JSON 视口聚焦交互
			switch msg.String() {
			case "enter":
				// 回车切回上方步骤栏
				m.traceFocusJSON = false
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

// viewTraceInspector 渲染上下折叠的底层 JSON 追踪看板
func (m Model) viewTraceInspector() string {
	cardWidth := max(70, min(m.width-2, 120))
	cardHeight := max(16, min(m.height-2, 38))
	boxWidth := cardWidth - 6
	vpWidth := max(30, boxWidth-2)
	vpHeight := max(6, cardHeight-15)

	m.traceViewport.Width = vpWidth
	m.traceViewport.Height = vpHeight

	// 1. 顶部 Header 状态信息
	badge := bentoTitleBadgeStyle.Render(" Tide ")
	title := lipgloss.NewStyle().Bold(true).Foreground(colorTextNormal).Render(" 全系统执行链路与底层 JSON 追踪看板")

	modeHint := lipgloss.NewStyle().Foreground(colorGreen).Render("● 纯净底层 JSON (已剔除静态配置与无用 Schema，按 r 切换全量)")
	if m.traceRawMode {
		modeHint = lipgloss.NewStyle().Foreground(colorYellow).Render("● 全量原始报文 (Raw Wire Protocol，按 r 切回纯净模式)")
	}

	sub := dimStyle.Render(fmt.Sprintf("当前捕获事件: %d 个 · %s", len(m.traceEvents), modeHint))
	headerBlock := fmt.Sprintf("%s %s\n%s\n", badge, title, sub)

	// 2. 上部：步骤时序列表（带滑动窗口，固定展示 5 行，杜绝拉扯抖动）
	var stepListSB strings.Builder
	stepHeader := lipgloss.NewStyle().Bold(true).Foreground(colorOrange).Render("📋 执行时序流 (按 ↑/↓ 切换步骤，Enter 进入下方视口)")
	stepListSB.WriteString(stepHeader + "\n")

	if len(m.traceEvents) == 0 {
		stepListSB.WriteString(dimStyle.Render("  暂无事件记录\n"))
	} else {
		maxVisible := 5
		startIdx := 0
		if m.traceCursor >= maxVisible {
			startIdx = m.traceCursor - maxVisible + 1
		}
		endIdx := min(len(m.traceEvents), startIdx+maxVisible)

		for i := startIdx; i < endIdx; i++ {
			ev := m.traceEvents[i]
			cursor := "  "
			if m.traceCursor == i {
				cursor = cursorStyle.Render("▶ ")
			}

			titleText := ev.Title
			maxTitleLen := boxWidth - 6
			if maxTitleLen > 10 && len([]rune(titleText)) > maxTitleLen {
				titleText = string([]rune(titleText)[:maxTitleLen-3]) + "..."
			}

			var line string
			if m.traceCursor == i {
				if !m.traceFocusJSON {
					line = lipgloss.NewStyle().Bold(true).Foreground(colorBrandLight).Render(titleText)
				} else {
					line = lipgloss.NewStyle().Bold(true).Foreground(colorCyan).Render(titleText)
				}
			} else {
				line = dimStyle.Render(titleText)
			}
			stepListSB.WriteString(fmt.Sprintf("%s%s\n", cursor, line))
		}
	}

	stepBorderColor := colorBorder
	if !m.traceFocusJSON {
		stepBorderColor = colorBrand
	}
	stepListBox := lipgloss.NewStyle().
		Width(boxWidth).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(stepBorderColor).
		Background(colorSurface).
		Padding(0, 1).
		Render(strings.TrimRight(stepListSB.String(), "\n"))

	// 3. 下部：全宽 JSON 展开视口
	selectedTitle := "底层 JSON 报文"
	if m.traceCursor >= 0 && m.traceCursor < len(m.traceEvents) {
		selectedTitle = m.traceEvents[m.traceCursor].Title
	}

	scrollPercent := int(m.traceViewport.ScrollPercent() * 100)
	vpHeader := lipgloss.NewStyle().Bold(true).Foreground(colorCyan).Render(fmt.Sprintf("📦 %s", selectedTitle))
	vpHint := dimStyle.Render(fmt.Sprintf(" [已滚至 %d%%]", scrollPercent))

	var jsonSB strings.Builder
	jsonSB.WriteString(vpHeader + vpHint + "\n")
	jsonSB.WriteString(m.traceViewport.View())

	jsonBorderColor := colorBorder
	if m.traceFocusJSON {
		jsonBorderColor = colorBrand
	}
	jsonBox := lipgloss.NewStyle().
		Width(boxWidth).
		Height(vpHeight+2).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(jsonBorderColor).
		Background(colorSurface).
		Padding(0, 1).
		Render(jsonSB.String())

	// 4. 底部快捷操作指引
	focusText := "当前焦点: 上方步骤列表"
	if m.traceFocusJSON {
		focusText = "当前焦点: 下方全宽 JSON 视口 (可用 ↑/↓/PgUp/PgDn 滚动)"
	}
	footer := fmt.Sprintf("%s  %s 切换步骤  %s 切换上下焦点  %s 切换Clean/Raw  %s 滚动  %s 返回",
		lipgloss.NewStyle().Foreground(colorYellow).Render(focusText),
		keycapPillStyle.Render("[↑/↓, k/j]"),
		keycapPillStyle.Render("[Tab/Enter]"),
		keycapPillStyle.Render("[r]"),
		keycapPillStyle.Render("[PgUp/PgDn]"),
		keycapPillStyle.Render("[Esc/q]"),
	)
	footerBlock := footerStyle.Render(footer)

	// 5. 纯垂直流自然堆叠 (JoinVertical)，杜绝横向碰撞与穿透
	body := lipgloss.JoinVertical(lipgloss.Left,
		headerBlock,
		stepListBox,
		"\n",
		jsonBox,
		"\n",
		footerBlock,
	)

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorBorderActive).
		Background(colorSurface).
		Padding(0, 1).
		Width(cardWidth).
		Render(body) + "\n"
}
