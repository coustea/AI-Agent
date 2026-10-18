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

	colorReasoning     = lipgloss.Color("#A78BFA") // 思考链薰衣草紫 (Violet)
	colorReasoningText = lipgloss.Color("#DDD6FE") // 思考链柔和高对比文本

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

	dimStyle = lipgloss.NewStyle().
			Foreground(colorTextMuted)

	promptPrefixStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorBrand)

	// ==========================================
	// 4. 深度思考链与思考看板专用样式
	// ==========================================
	reasoningTextStyle = lipgloss.NewStyle().
				Foreground(colorReasoningText).
				Italic(true)

	reasoningTitleStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorReasoning)

	thinkingBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorReasoning).
				Foreground(lipgloss.Color("#1A1D24")).
				Padding(0, 1)

	thinkingTabActiveStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorReasoning).
				Foreground(lipgloss.Color("#1A1D24")).
				Padding(0, 1)

	thinkingTabInactiveStyle = lipgloss.NewStyle().
					Background(colorSurface).
					Foreground(colorTextMuted).
					Padding(0, 1)

	thinkingCardStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorReasoning).
				Background(colorSurface).
				Padding(0, 1)

	// ==========================================
	// 5. 工具卡片与状态芯片样式
	// ==========================================
	toolHeaderStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorOrange)

	toolRunningStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorYellow)

	// 工具 Bento 卡片容器与徽章样式
	toolCardRunningStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorYellow).
				Background(colorYellowSubtle).
				Padding(0, 1)

	toolCardSuccessStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorGreen).
				Background(colorGreenSubtle).
				Padding(0, 1)

	toolCardErrorStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorRed).
				Background(colorRedSubtle).
				Padding(0, 1)

	toolBadgeRunning = lipgloss.NewStyle().
				Bold(true).
				Background(colorYellow).
				Foreground(lipgloss.Color("#1A1D24")).
				Padding(0, 1)

	toolBadgeSuccess = lipgloss.NewStyle().
				Bold(true).
				Background(colorGreen).
				Foreground(lipgloss.Color("#1A1D24")).
				Padding(0, 1)

	toolBadgeError = lipgloss.NewStyle().
			Bold(true).
			Background(colorRed).
			Foreground(lipgloss.Color("#FFFFFF")).
			Padding(0, 1)

	// ==========================================
	// 6. 权限审批 Gate 3 交互与审计卡片样式
	// ==========================================
	permissionWarnStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorYellow)

	permissionAuditAllowedStyle = lipgloss.NewStyle().
					Border(lipgloss.RoundedBorder()).
					BorderForeground(colorGreen).
					Background(colorGreenSubtle).
					Padding(0, 1)

	permissionAuditDeniedStyle = lipgloss.NewStyle().
					Border(lipgloss.RoundedBorder()).
					BorderForeground(colorRed).
					Background(colorRedSubtle).
					Padding(0, 1)

	permissionAuditBadgeAllowed = lipgloss.NewStyle().
					Bold(true).
					Background(colorGreen).
					Foreground(lipgloss.Color("#1A1D24")).
					Padding(0, 1)

	permissionAuditBadgeDenied = lipgloss.NewStyle().
					Bold(true).
					Background(colorRed).
					Foreground(lipgloss.Color("#FFFFFF")).
					Padding(0, 1)

	permissionAuditDecisionAllow = lipgloss.NewStyle().
					Bold(true).
					Foreground(colorGreen)

	permissionAuditDecisionDeny = lipgloss.NewStyle().
					Bold(true).
					Foreground(colorRed)

	// 卡片通用字段标签与代码块样式
	cardLabelOrange = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorOrange)

	cardLabelCyan = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorCyan)

	cardLabelRed = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorRed)

	cardLabelGreen = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorGreen)

	cardLabelYellow = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorYellow)

	codeArgStyle = lipgloss.NewStyle().
			Background(colorSurface).
			Foreground(colorCyan).
			Padding(0, 1)

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
	statusReadyStyle = lipgloss.NewStyle().
				Foreground(colorGreen).
				Bold(true)

	statusThinkingStyle = lipgloss.NewStyle().
				Foreground(colorYellow).
				Bold(true)

	cursorStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorBrand)

	selectedStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorGreen)

	footerStyle = lipgloss.NewStyle().
			Foreground(colorTextMuted)

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
