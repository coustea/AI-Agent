package tui

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	// 主题色彩（Claude Code 质感配色）
	colorCoral  = lipgloss.Color("#D97757") // Claude 暖珊瑚色
	colorOrange = lipgloss.Color("#E59866") // 辅助暖色
	colorGray   = lipgloss.Color("#6272A4") // 辅助弱色
	colorDim    = lipgloss.Color("#7F848E") // 占位与灰色提示
	colorGreen  = lipgloss.Color("#50FA7B") // 成功/就绪绿
	colorCyan   = lipgloss.Color("#8BE9FD") // 青色高亮

	// 样式定义
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorCoral)

	badgeStyle = lipgloss.NewStyle().
			Bold(true).
			Background(colorCoral).
			Foreground(lipgloss.Color("#FFFFFF")).
			Padding(0, 1)

	cursorStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorCoral)

	selectedStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorGreen)

	dimStyle = lipgloss.NewStyle().
			Foreground(colorDim)

	promptPrefixStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorCoral)

	userPrefixStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorCyan)

	assistantPrefixStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorCoral)

	footerStyle = lipgloss.NewStyle().
			Foreground(colorDim)

	toolCallStyle = lipgloss.NewStyle().
			Foreground(colorOrange).
			Italic(true)

	toolResultSuccessStyle = lipgloss.NewStyle().
				Foreground(colorGreen)

	toolResultErrorStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#FF5555"))

	permissionBoxStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(lipgloss.Color("#FFB86C")).
				Padding(0, 1)

	permissionWarnStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(lipgloss.Color("#FFB86C"))
)
