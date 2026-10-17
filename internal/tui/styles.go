package tui

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	// ==========================================
	// 1. 现代化调色系统 (Tokyo Night / Claude Dark)
	// ==========================================
	colorBrand       = lipgloss.Color("#FF7A59") // Claude 暖珊瑚活力橙
	colorBrandLight  = lipgloss.Color("#FFA07A") // 亮珊瑚高光色
	colorBrandSubtle = lipgloss.Color("#2D1F1D") // 品牌微透暗底

	colorUser       = lipgloss.Color("#38BDF8") // 用户输入与高亮 (Sky Blue)
	colorUserSubtle = lipgloss.Color("#162938") // 用户卡片微暗底

	colorReasoning       = lipgloss.Color("#A78BFA") // 思考链薰衣草紫 (Violet)
	colorReasoningSubtle = lipgloss.Color("#231E33") // 思考链微暗底
	colorReasoningText   = lipgloss.Color("#DDD6FE") // 思考链柔和高对比文本

	colorGreen       = lipgloss.Color("#34D399") // 成功、激活与就绪 (Emerald)
	colorGreenSubtle = lipgloss.Color("#132F23") // 成功微绿暗底

	colorYellow       = lipgloss.Color("#FBBF24") // 待审批与运行中提醒 (Amber)
	colorYellowSubtle = lipgloss.Color("#332814") // 警告微黄暗底

	colorRed       = lipgloss.Color("#F43F5E") // 阻断、报错与危险 (Rose Red)
	colorRedSubtle = lipgloss.Color("#38171E") // 报错微红暗底

	colorOrange = lipgloss.Color("#FB923C") // 工具名称与提示 (Orange)
	colorCyan   = lipgloss.Color("#22D3EE") // 细节高亮青色

	colorSurface      = lipgloss.Color("#1E222D") // 悬浮卡片背景深灰
	colorBorder       = lipgloss.Color("#333A4C") // 柔和卡片边框灰
	colorBorderActive = lipgloss.Color("#4F5B75") // 激活态高亮边框灰

	colorTextNormal = lipgloss.Color("#E2E8F0") // 正文高对比度白灰
	colorTextMuted  = lipgloss.Color("#94A3B8") // 辅助文本浅灰
	colorDim        = lipgloss.Color("#64748B") // 弱化文本暗灰

	// 兼容旧别名
	colorCoral      = colorBrand
	colorCoralLight = colorBrandLight
	colorPurple     = colorReasoning
	colorBgSubtle   = colorSurface

	// ==========================================
	// 2. 顶部 Header 状态栏样式
	// ==========================================
	headerBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorBrand).
				Foreground(lipgloss.Color("#FFFFFF")).
				Padding(0, 1)

	headerTagStyle = lipgloss.NewStyle().
			Bold(true).
			Background(colorSurface).
			Foreground(colorUser).
			Padding(0, 1)

	headerMemoryStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorGreenSubtle).
				Foreground(colorGreen).
				Padding(0, 1)

	headerDirStyle = lipgloss.NewStyle().
			Foreground(colorTextMuted)

	headerDividerStyle = lipgloss.NewStyle().
				Foreground(colorBorder)

	// ==========================================
	// 3. 消息流与角色气泡徽章样式
	// ==========================================
	userBadgeStyle = lipgloss.NewStyle().
			Bold(true).
			Background(colorUserSubtle).
			Foreground(colorUser).
			Padding(0, 1)

	userPromptTextStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorTextNormal)

	assistantBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorBrandSubtle).
				Foreground(colorBrand).
				Padding(0, 1)

	systemBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorSurface).
				Foreground(colorTextMuted).
				Padding(0, 1)

	tokenBadgeStyle = lipgloss.NewStyle().
			Background(colorSurface).
			Foreground(colorTextMuted).
			Padding(0, 1)

	userPrefixStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorUser)

	assistantPrefixStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorBrand)

	systemPrefixStyle = lipgloss.NewStyle().
				Foreground(colorTextMuted)

	dimStyle = lipgloss.NewStyle().
			Foreground(colorTextMuted)

	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorBrand)

	promptPrefixStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorBrand)

	// ==========================================
	// 4. 可折叠深度思考链 (Reasoning Box)
	// ==========================================
	reasoningBoxStyle = lipgloss.NewStyle().
				Border(lipgloss.NormalBorder(), false, false, false, true).
				BorderForeground(colorReasoning).
				Background(colorReasoningSubtle).
				Padding(0, 1).
				Foreground(colorReasoningText)

	reasoningTextStyle = lipgloss.NewStyle().
				Foreground(colorReasoningText).
				Italic(true)

	reasoningTitleStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorReasoning)

	// ==========================================
	// 5. 工具卡片与状态芯片样式
	// ==========================================
	toolCardBoxStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorBorder).
				Background(colorSurface).
				Padding(0, 1)

	toolHeaderStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorOrange)

	toolRunningStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorYellow)

	toolResultSuccessStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorGreen)

	toolResultErrorStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorRed)

	toolSnippetStyle = lipgloss.NewStyle().
				Foreground(colorTextMuted)

	// ==========================================
	// 6. 权限审批 Gate 3 交互卡片样式
	// ==========================================
	permissionBoxStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorYellow).
				Background(colorYellowSubtle).
				Padding(0, 1)

	permissionWarnStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorYellow)

	keycapAllowStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorGreenSubtle).
				Foreground(colorGreen).
				Padding(0, 1)

	keycapSessionStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorYellowSubtle).
				Foreground(colorYellow).
				Padding(0, 1)

	keycapDenyStyle = lipgloss.NewStyle().
			Bold(true).
			Background(colorRedSubtle).
			Foreground(colorRed).
			Padding(0, 1)

	// ==========================================
	// 7. 运行状态、滚动条与按键胶囊
	// ==========================================
	statusBarBoxStyle = lipgloss.NewStyle().
				Background(colorSurface).
				Foreground(colorTextNormal).
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

	statusUnsetStyle = lipgloss.NewStyle().
				Foreground(colorDim)

	cursorStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorBrand)

	selectedStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorGreen)

	footerStyle = lipgloss.NewStyle().
			Foreground(colorTextMuted)

	keycapStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorBrandLight)

	keycapPillStyle = lipgloss.NewStyle().
			Background(colorSurface).
			Foreground(colorBrandLight).
			Bold(true).
			Padding(0, 1)

	scrollIndicatorStyle = lipgloss.NewStyle().
				Foreground(colorTextMuted).
				Italic(true)

	// ==========================================
	// 8. Bento 模型看板与弹窗交互样式
	// ==========================================
	bentoTitleBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorBrand).
				Foreground(lipgloss.Color("#FFFFFF")).
				Padding(0, 1)

	bentoReadyBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorGreenSubtle).
				Foreground(colorGreen).
				Padding(0, 1)

	bentoUnsetBadgeStyle = lipgloss.NewStyle().
				Foreground(colorDim).
				Background(colorSurface).
				Padding(0, 1)

	bentoModelChipStyle = lipgloss.NewStyle().
				Foreground(colorYellow).
				Background(colorSurface).
				Padding(0, 1)

	bentoActiveItemStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorBrandLight)

	bentoNormalItemStyle = lipgloss.NewStyle().
				Foreground(colorTextNormal)

	// ==========================================
	// 9. Command Dock (控制台悬浮驾驶舱) 样式
	// ==========================================
	dockPromptBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorBrand).
				Foreground(lipgloss.Color("#FFFFFF")).
				Padding(0, 1)

	dockGeneratingBadgeStyle = lipgloss.NewStyle().
					Bold(true).
					Background(colorYellowSubtle).
					Foreground(colorYellow).
					Padding(0, 1)

	dockPermissionBadgeStyle = lipgloss.NewStyle().
					Bold(true).
					Background(colorYellowSubtle).
					Foreground(colorYellow).
					Padding(0, 1)

	dockModelTagStyle = lipgloss.NewStyle().
				Background(colorSurface).
				Foreground(colorCyan).
				Padding(0, 1)

	dockDividerStyle = lipgloss.NewStyle().
				Foreground(colorBorder)
)
