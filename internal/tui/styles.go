package tui

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	// ==========================================
	// 1. 现代潮汐深空调色系统 (Tide Modern / Deep Abyssal)
	// ==========================================
	colorBrand       = lipgloss.Color("#38BDF8") // 潮汐天蓝 (Sky Blue 主品牌色)
	colorBrandLight  = lipgloss.Color("#7DD3FC") // 潮汐浪花浅蓝 (高亮文字)
	colorBrandSubtle = lipgloss.Color("#0F2231") // 品牌微透暗底

	colorUser       = lipgloss.Color("#38BDF8") // 用户输入与高亮 (Sky Blue)
	colorUserSubtle = lipgloss.Color("#112233") // 用户卡片微暗底

	colorReasoning       = lipgloss.Color("#A78BFA") // 思考链晶体紫 (Violet)
	colorReasoningText   = lipgloss.Color("#DDD6FE") // 思考链柔和高对比文本
	colorReasoningSubtle = lipgloss.Color("#1E1B2E") // 思考微紫暗底

	colorGreen       = lipgloss.Color("#10B981") // 成功、激活与就绪 (Emerald)
	colorGreenLight  = lipgloss.Color("#6EE7B7") // 浅海绿高光
	colorGreenSubtle = lipgloss.Color("#062E20") // 成功微绿暗底

	colorYellow       = lipgloss.Color("#F59E0B") // 待审批与进行中 (Amber)
	colorYellowLight  = lipgloss.Color("#FDE68A") // 琥珀亮金
	colorYellowSubtle = lipgloss.Color("#2A1D08") // 警告微黄暗底

	colorRed       = lipgloss.Color("#F43F5E") // 阻断、报错与危险 (Rose Red)
	colorRedLight  = lipgloss.Color("#FDA4AF") // 浅玫瑰红
	colorRedSubtle = lipgloss.Color("#2E0D14") // 报错微红暗底

	colorOrange = lipgloss.Color("#FB923C") // 工具名称与高亮 (Warm Orange)
	colorCyan   = lipgloss.Color("#2DD4BF") // 浪花青色 (Teal Cyan)

	colorSurface      = lipgloss.Color("#161B22") // 悬浮卡片背景深灰 (GitHub Dark / Raycast)
	colorSurfaceAlt   = lipgloss.Color("#21262D") // 次级容器轻质衬底
	colorBorder       = lipgloss.Color("#30363D") // 柔和微暗边框灰 (低侵入性)
	colorBorderActive = lipgloss.Color("#38BDF8") // 激活态高亮天蓝边框
	colorBorderViolet = lipgloss.Color("#8B5CF6") // 思考链微光边框

	colorTextNormal = lipgloss.Color("#F0F6FC") // 正文高对比度白灰
	colorTextMuted  = lipgloss.Color("#8B949E") // 辅助文本浅灰
	colorDim        = lipgloss.Color("#484F58") // 弱化文本暗灰 (微图标/折叠)

	// ==========================================
	// 2. 顶部 Header 状态栏样式 (极简单行 Flex 布局)
	// ==========================================
	headerBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorBrand).
				Foreground(lipgloss.Color("#0B0F14")).
				Padding(0, 1)

	headerTagStyle = lipgloss.NewStyle().
			Background(colorSurface).
			Foreground(colorBrandLight).
			Padding(0, 1)

	headerMemoryStyle = lipgloss.NewStyle().
				Background(colorGreenSubtle).
				Foreground(colorGreenLight).
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

	userBlockContainer = lipgloss.NewStyle().
				BorderLeft(true).
				BorderStyle(lipgloss.ThickBorder()).
				BorderForeground(colorBrand).
				PaddingLeft(1)

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
			Foreground(colorTextMuted).
			Italic(true)

	dimStyle = lipgloss.NewStyle().
			Foreground(colorTextMuted)

	promptPrefixStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorBrand)

	// ==========================================
	// 4. 深度思考链与思考看板专用样式
	// ==========================================
	reasoningTextStyle = lipgloss.NewStyle().
				Foreground(colorReasoningText)

	reasoningTitleStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorReasoning)

	thinkingCapsuleStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorBorderViolet).
				Background(colorReasoningSubtle).
				Padding(0, 1)

	thinkingBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorReasoning).
				Foreground(lipgloss.Color("#0B0F14")).
				Padding(0, 1)

	thinkingTabActiveStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorReasoning).
				Foreground(lipgloss.Color("#0B0F14")).
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
	// 5. 工具卡片与状态芯片样式 (DevTools Bento 风格)
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
				BorderForeground(colorBorder).
				Background(colorSurface).
				Padding(0, 1)

	toolCardErrorStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorRed).
				Background(colorRedSubtle).
				Padding(0, 1)

	toolBadgeRunning = lipgloss.NewStyle().
				Bold(true).
				Background(colorYellow).
				Foreground(lipgloss.Color("#0B0F14")).
				Padding(0, 1)

	toolBadgeSuccess = lipgloss.NewStyle().
				Bold(true).
				Background(colorGreen).
				Foreground(lipgloss.Color("#0B0F14")).
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
					Foreground(lipgloss.Color("#0B0F14")).
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
			Background(colorSurfaceAlt).
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
	// 7. 运行状态、滚动条与按键胶囊 (Kbd Badges)
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

	// 键盘按键拟物质感标签 (Kbd Pill)
	keycapPillStyle = lipgloss.NewStyle().
			Background(colorSurfaceAlt).
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
				Foreground(lipgloss.Color("#0B0F14")).
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
	// 9. Command Dock (悬浮命令岛驾驶舱) 样式
	// ==========================================
	dockPromptBadgeStyle = lipgloss.NewStyle().
				Bold(true).
				Background(colorBrandSubtle).
				Foreground(colorBrand).
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
				Background(colorSurfaceAlt).
				Foreground(colorCyan).
				Padding(0, 1)

	dockDividerStyle = lipgloss.NewStyle().
				Foreground(colorBorder)
)
