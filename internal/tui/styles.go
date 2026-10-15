package tui

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	// 主题色彩（Claude Code 质感配色）
	colorCoral      = lipgloss.Color("#D97757") // Claude 暖珊瑚主色
	colorCoralLight = lipgloss.Color("#E8927C") // 亮珊瑚色
	colorOrange     = lipgloss.Color("#FFB86C") // 警告与工具橙色
	colorPurple     = lipgloss.Color("#BD93F9") // 思考链淡紫色
	colorDim        = lipgloss.Color("#6272A4") // 占位与柔和提示色
	colorGreen      = lipgloss.Color("#50FA7B") // 成功与就绪绿
	colorRed        = lipgloss.Color("#FF5555") // 报错与危险红
	colorYellow     = lipgloss.Color("#F1FA8C") // 审批与提醒黄
	colorCyan       = lipgloss.Color("#8BE9FD") // 用户输入高亮青色
	colorBgSubtle   = lipgloss.Color("#282A36") // 弱背景底色
	colorBorder     = lipgloss.Color("#44475A") // 边框底色

	// 1. 顶部 Header 样式
	headerBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorCoral).
				Foreground(lipgloss.Color("#FFFFFF")).
				Padding(0, 1)

	headerTagStyle = lipgloss.NewStyle().
			Bold(true).
			Background(colorBgSubtle).
			Foreground(colorCyan).
			Padding(0, 1)

	headerMemoryStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorBgSubtle).
				Foreground(colorGreen).
				Padding(0, 1)

	headerDirStyle = lipgloss.NewStyle().
			Foreground(colorDim)

	headerDividerStyle = lipgloss.NewStyle().
				Foreground(colorBorder)

	// 2. 消息前缀样式
	userPrefixStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorCyan)

	assistantPrefixStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorCoral)

	systemPrefixStyle = lipgloss.NewStyle().
				Foreground(colorDim)

	dimStyle = lipgloss.NewStyle().
			Foreground(colorDim)

	cursorStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorCoral)

	selectedStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorGreen)

	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorCoral)

	promptPrefixStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorCoral)

	// 3. 思考链 (Reasoning Content) 样式
	reasoningBoxStyle = lipgloss.NewStyle().
				Border(lipgloss.NormalBorder(), false, false, false, true).
				BorderForeground(colorPurple).
				PaddingLeft(1).
				Foreground(lipgloss.Color("#BFB4D6")).
				Italic(true)

	reasoningTitleStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorPurple)

	// 4. 工具卡片样式
	toolCardBoxStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorBorder).
				Padding(0, 1)

	toolHeaderStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorOrange)

	toolRunningStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorYellow)

	toolResultSuccessStyle = lipgloss.NewStyle().
				Foreground(colorGreen)

	toolResultErrorStyle = lipgloss.NewStyle().
				Foreground(colorRed)

	toolSnippetStyle = lipgloss.NewStyle().
				Foreground(colorDim)

	// 5. 权限审批 Gate 3 卡片样式
	permissionBoxStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorYellow).
				Padding(0, 1)

	permissionWarnStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorYellow)

	// 6. 状态栏与滚动提示
	statusBarBoxStyle = lipgloss.NewStyle().
				Background(colorBgSubtle).
				Foreground(lipgloss.Color("#FFFFFF")).
				Padding(0, 1)

	statusReadyStyle = lipgloss.NewStyle().
				Foreground(colorGreen).
				Bold(true)

	statusThinkingStyle = lipgloss.NewStyle().
				Foreground(colorYellow).
				Bold(true)

	statusToolStyle = lipgloss.NewStyle().
			Foreground(colorOrange).
			Bold(true)

	footerStyle = lipgloss.NewStyle().
			Foreground(colorDim)

	scrollIndicatorStyle = lipgloss.NewStyle().
				Foreground(colorDim).
				Italic(true)
)
