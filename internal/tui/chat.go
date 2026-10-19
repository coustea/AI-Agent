package tui

import (
	"context"
	"fmt"
	"os"
	"strings"

	"my-agent/internal/protocol"
	"my-agent/internal/textutil"
	"my-agent/pkg/llm"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ToolCallRecord 结构化记录单次工具调用过程与结果，组合统一的 ToolCall 与 ToolResult
type ToolCallRecord struct {
	Call   llm.ToolCall
	Result *llm.ToolResult
}

// BlockKind 定义消息片段类型
type BlockKind int

const (
	BlockReasoning  BlockKind = iota // 思考链片段
	BlockText                        // 普通文本片段
	BlockTool                        // 工具调用与结果卡片
	BlockPermission                  // 权限拦截与审批审计卡片
)

// PermissionRecord 记录一次权限拦截与用户的审批决策结果
type PermissionRecord struct {
	Request  protocol.PermissionRequest
	Decision protocol.Decision
}

// MessageBlock 描述消息内部的一个有序展示块，严格按照到达先后顺序线性排列
type MessageBlock struct {
	Kind       BlockKind
	Text       string
	Tool       *ToolCallRecord
	Permission *PermissionRecord
}

// ChatMessage 用于在界面上展示发送和接收的消息
type ChatMessage struct {
	Sender  string         // "You", "Tide", "System"
	Content string         // 文本内容 (用户输入、系统提示或回退兜底)
	Blocks  []MessageBlock // 严格按时间线性排列的结构化块 (思考、文本、工具、权限)
	Usage   *llm.Usage     // 携带的 Token 用量统计（可选）
}

// updateChat 处理聊天页面的键盘输入和发送逻辑
func (m Model) updateChat(msg tea.Msg) (tea.Model, tea.Cmd) {
	if keyMsg, ok := msg.(tea.KeyMsg); ok {
		// 1. 若当前存在挂起的权限审批请求，优先处理审批交互
		if m.pendingPerm != nil {
			reqID := m.pendingPerm.RequestID
			switch keyMsg.String() {
			case "y", "Y":
				_ = m.agent.RespondPermission(reqID, protocol.DecisionAllowOnce)
				if len(m.messages) > 0 {
					m.messages[len(m.messages)-1].Blocks = append(m.messages[len(m.messages)-1].Blocks, MessageBlock{
						Kind: BlockPermission,
						Permission: &PermissionRecord{
							Request:  *m.pendingPerm,
							Decision: protocol.DecisionAllowOnce,
						},
					})
				}
				m.pendingPerm = nil
				m.chatInput.Placeholder = "Tide 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"
				m.updateViewportDimensions()
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			case "a", "A":
				_ = m.agent.RespondPermission(reqID, protocol.DecisionAllowSession)
				if len(m.messages) > 0 {
					m.messages[len(m.messages)-1].Blocks = append(m.messages[len(m.messages)-1].Blocks, MessageBlock{
						Kind: BlockPermission,
						Permission: &PermissionRecord{
							Request:  *m.pendingPerm,
							Decision: protocol.DecisionAllowSession,
						},
					})
				}
				m.pendingPerm = nil
				m.chatInput.Placeholder = "Tide 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"
				m.updateViewportDimensions()
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			case "n", "N":
				_ = m.agent.RespondPermission(reqID, protocol.DecisionDeny)
				if len(m.messages) > 0 {
					m.messages[len(m.messages)-1].Blocks = append(m.messages[len(m.messages)-1].Blocks, MessageBlock{
						Kind: BlockPermission,
						Permission: &PermissionRecord{
							Request:  *m.pendingPerm,
							Decision: protocol.DecisionDeny,
						},
					})
				}
				m.pendingPerm = nil
				m.chatInput.Placeholder = "Tide 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"
				m.updateViewportDimensions()
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}

			if keyMsg.Type == tea.KeyEsc {
				_ = m.agent.RespondPermission(reqID, protocol.DecisionDeny)
				if len(m.messages) > 0 {
					m.messages[len(m.messages)-1].Blocks = append(m.messages[len(m.messages)-1].Blocks, MessageBlock{
						Kind: BlockPermission,
						Permission: &PermissionRecord{
							Request:  *m.pendingPerm,
							Decision: protocol.DecisionDeny,
						},
					})
				}
				m.pendingPerm = nil
				m.chatInput.Placeholder = "Tide 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"
				m.updateViewportDimensions()
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}

			// 处于权限审批等待状态时，屏蔽其他输入
			return m, nil
		}

		// 2. 历史记录专由鼠标滚轮上下滑动查看；
		// 屏蔽上下方向键/翻页键对视口滚动的拦截与篡改，保障输入框永远常驻底部不抖动、不消失。
		switch keyMsg.Type {
		case tea.KeyUp, tea.KeyDown, tea.KeyPgUp, tea.KeyPgDown:
			return m, nil

		case tea.KeyEnter:
			// 如果正在流式生成中，避免重复触发
			if m.isGenerating {
				return m, nil
			}

			text := strings.TrimSpace(m.chatInput.Value())
			if text == "" {
				return m, nil
			}

			// 拦截并分发快捷指令（委托给 command.go / config_wizard.go 处理，chat.go 纯粹负责聊天设计与交互）
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
				Sender:  "Tide",
				Content: "",
			})
			m.isGenerating = true
			m.chatInput.Placeholder = "Tide 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"

			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}

			// 未就绪校验：远程厂商缺密钥时先引导配置（本地服务恒就绪）
			if !m.agent.Config().HasAPIKey {
				m.messages[len(m.messages)-1].Content = "[未配置可用模型] 请先输入 /model 配置 API Key 或设置环境变量 (DEEPSEEK_API_KEY / GEMINI_API_KEY)。"
				m.isGenerating = false
				m.chatInput.Placeholder = "输入消息与 Tide 对话... (输入 /log 查看全量JSON, /model 切换模型, /clear 清屏)"
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}

			ctx, cancel := context.WithCancel(context.Background())
			m.cancel = cancel
			ch, err := m.agent.Run(ctx, text)
			if err != nil {
				m.cancel = nil
				m.messages[len(m.messages)-1].Content = fmt.Sprintf("[请求失败: %v]", err)
				m.isGenerating = false
				m.chatInput.Placeholder = "输入消息与 Tide 对话... (输入 /log 查看全量JSON, /model 切换模型, /clear 清屏)"
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

// shortenPath 友好缩写工作区路径（例如用 ~ 代替用户主目录，超长时截短）
func shortenPath(path string, maxLen int) string {
	p := strings.TrimSpace(path)
	if p == "" {
		return "."
	}
	if home, err := os.UserHomeDir(); err == nil && home != "" {
		if strings.HasPrefix(p, home) {
			p = "~" + strings.TrimPrefix(p, home)
		}
	}
	if len(p) > maxLen && maxLen > 10 {
		return "..." + p[len(p)-(maxLen-3):]
	}
	return p
}

// updateViewportDimensions 动态精确计算聊天页面视口尺寸，确保总行数严丝合缝匹配终端高度
func (m *Model) updateViewportDimensions() {
	if m.width <= 0 || m.height <= 0 {
		return
	}
	cardWidth := max(50, m.width-4)
	m.chatInput.Width = max(36, cardWidth-8)

	headerHeight := lipgloss.Height(m.renderHeaderBar())
	inputHeight := lipgloss.Height(m.renderInputBox())
	permHeight := 0
	if m.pendingPerm != nil {
		permHeight = lipgloss.Height(m.renderPermissionCard()) + 1
	}

	// 视口高度 = 终端总高度 - 固定组件高度 (Header + InputBox + 审批卡片)
	nonViewportHeight := headerHeight + permHeight + inputHeight
	vpHeight := max(4, m.height-nonViewportHeight)

	m.viewport.Width = max(40, m.width-2)
	m.viewport.Height = vpHeight
	m.viewportReady = true
}

// renderHeaderBar 渲染固定在顶部的 Tide 现代极简品牌与状态栏 (严格单行 + 水平细线)
func (m Model) renderHeaderBar() string {
	cfg := m.agent.Config()
	modelInfo := "未配置模型 (/model)"
	if cfg.ModelName != "" {
		modelInfo = fmt.Sprintf("%s · %s", cfg.Provider, cfg.ModelName)
	}

	brandBadge := headerBadgeStyle.Render(" Tide ")
	modelTag := headerTagStyle.Render("● " + modelInfo)

	// 工作区目录优先展示：自适应截断
	availForDir := max(12, m.width-lipgloss.Width(brandBadge)-lipgloss.Width(modelTag)-16)
	shortDir := shortenPath(m.agent.WorkDir(), availForDir)
	dirTag := headerDirStyle.Render("📂 " + shortDir)

	// 生效记忆
	memTag := headerMemoryStyle.Render(fmt.Sprintf("🧠 %d 篇记忆", m.cachedMemCount))

	var headerRow string
	if m.width >= 80 {
		headerRow = fmt.Sprintf("%s %s %s %s", brandBadge, modelTag, memTag, dirTag)
	} else if m.width >= 55 {
		headerRow = fmt.Sprintf("%s %s %s", brandBadge, modelTag, dirTag)
	} else {
		headerRow = fmt.Sprintf("%s %s", brandBadge, modelTag)
	}

	// 严格截断保证单行
	headerRow = textutil.TruncateUTF8(headerRow, max(30, m.width-2))
	divider := headerDividerStyle.Render(strings.Repeat("─", max(30, m.width-2)))
	return fmt.Sprintf("%s\n%s", headerRow, divider)
}

// renderPermissionCard 渲染 Claude Code 风格高安全性 Gate 3 权限审批交互卡片
func (m Model) renderPermissionCard() string {
	if m.pendingPerm == nil {
		return ""
	}
	cardWidth := max(50, m.width-4)
	req := m.pendingPerm

	var sb strings.Builder
	title := cardLabelYellow.Render("🛡️  [权限审批 Gate 3] · 拦截潜在高危行为")
	sb.WriteString(title + "\n")

	sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelOrange.Render("⚡ 工具目标:"), req.ToolName))
	argPreview := codeArgStyle.Render(req.Arguments)
	sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelCyan.Render("📝 风险调用:"), argPreview))
	sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelRed.Render("⚠️  拦截原因:"), req.Reason))

	divider := dockDividerStyle.Render(strings.Repeat("─", max(20, cardWidth-6)))
	sb.WriteString(divider + "\n")

	actions := fmt.Sprintf("  %s %s   %s %s   %s %s",
		keycapAllowStyle.Render("[y] 允许本次"),
		dimStyle.Render("(单次放行)"),
		keycapSessionStyle.Render("[a] 本会话始终允许"),
		dimStyle.Render("(信任同类)"),
		keycapDenyStyle.Render("[n/Esc] 阻断执行"),
		dimStyle.Render("(安全拦截)"),
	)
	sb.WriteString(actions)

	return toolCardRunningStyle.Width(cardWidth).Render(sb.String())
}

// renderInputBox 渲染悬浮命令岛交互控制台驾驶舱 (Floating Command Dock)
func (m Model) renderInputBox() string {
	cardWidth := max(50, m.width-4)
	innerW := max(30, cardWidth-4)

	borderCol := colorBorderActive
	var statusBadge string

	if m.pendingPerm != nil {
		borderCol = colorYellow
		statusBadge = dockPermissionBadgeStyle.Render(" 🛡️ 权限审批决策中 ")
	} else if m.activeToolName != "" {
		borderCol = colorBrand
		statusBadge = dockGeneratingBadgeStyle.Render(fmt.Sprintf(" ⚙️ 正在调用 [%s]... ", m.activeToolName))
	} else if m.isGenerating {
		borderCol = colorYellow
		statusBadge = dockGeneratingBadgeStyle.Render(" ⏳ 思考生成中 ")
	} else {
		borderCol = colorBorderActive
		statusBadge = dockPromptBadgeStyle.Render(" 💬 PROMPT · 对话模式 ")
	}

	cfg := m.agent.Config()
	modelBadge := ""
	if cfg.ModelName != "" {
		readyDot := statusReadyStyle.Render("● 就绪")
		if m.isGenerating {
			readyDot = statusThinkingStyle.Render("⏳ 思考中")
		}
		modelBadge = dockModelTagStyle.Render(fmt.Sprintf("%s · %s", readyDot, cfg.ModelName))
	}

	// 视口滚动比例指示徽标
	scrollBadge := ""
	if m.viewportReady && m.viewport.TotalLineCount() > m.viewport.Height {
		percent := int(m.viewport.ScrollPercent() * 100)
		scrollBadge = scrollIndicatorStyle.Render(fmt.Sprintf("📜 %d%%", percent))
	}

	var topRow string
	if scrollBadge != "" && cardWidth >= 70 {
		topRow = fmt.Sprintf("%s  %s  %s", statusBadge, modelBadge, scrollBadge)
	} else if modelBadge != "" && cardWidth >= 55 {
		topRow = fmt.Sprintf("%s  %s", statusBadge, modelBadge)
	} else {
		topRow = statusBadge
	}
	topRow = textutil.TruncateUTF8(topRow, innerW)

	inputRow := textutil.TruncateUTF8(m.chatInput.View(), innerW)

	// 底部按键提示 (Kbd Badges，自适应宽度排版，杜绝换行撑破卡片)
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
		item := func(key, desc string) string {
			return fmt.Sprintf("%s %s", keycapPillStyle.Render(key), dimStyle.Render(desc))
		}
		sep := dimStyle.Render("  •  ")

		if cardWidth >= 95 {
			footerRow = fmt.Sprintf(" %s%s%s%s%s%s%s%s%s%s%s",
				item("Enter", "发送"),
				sep,
				item("滚轮", "历史"),
				sep,
				item("/think", "思考"),
				sep,
				item("/model", "模型"),
				sep,
				item("/log", "追踪"),
				sep,
				item("Ctrl+C", "退出"),
			)
		} else if cardWidth >= 75 {
			footerRow = fmt.Sprintf(" %s%s%s%s%s%s%s",
				item("Enter", "发送"),
				sep,
				item("/think", "思考"),
				sep,
				item("/model", "模型"),
				sep,
				item("Ctrl+C", "退出"),
			)
		} else {
			footerRow = fmt.Sprintf(" %s%s%s",
				item("Enter", "发送"),
				sep,
				item("Ctrl+C", "退出"),
			)
		}
	}
	footerRow = textutil.TruncateUTF8(footerRow, innerW)

	divider := dockDividerStyle.Render(strings.Repeat("─", innerW))
	dockContent := fmt.Sprintf("%s\n  %s\n%s\n%s", topRow, inputRow, divider, footerRow)

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderCol).
		Background(colorSurface).
		Padding(0, 1).
		Width(cardWidth).
		Render(dockContent)
}

// toolSemanticIcon 返回各内置工具专属的语义图标
func toolSemanticIcon(name string) string {
	switch name {
	case "bash":
		return "⚡ bash"
	case "read_file":
		return "📖 read_file"
	case "write_file":
		return "✏️ write_file"
	case "edit_file":
		return "📝 edit_file"
	case "glob":
		return "🌐 glob"
	case "grep":
		return "🔍 grep"
	default:
		return "⚙️ " + name
	}
}

// renderChatMessages 将所有历史消息格式化为适用于 Viewport 渲染的高质量通透呼吸卡片流
func (m Model) renderChatMessages() string {
	cardWidth := max(50, m.width-4)
	if len(m.messages) == 0 {
		title := lipgloss.NewStyle().Bold(true).Foreground(colorBrand).Render("🌊 欢迎使用 Tide 智能助手")
		text := "  在下方命令岛键入需求并按 Enter，Tide 将自主调用工具为您解决问题。\n" +
			"  常用指令: /model (切换模型平台), /think (打开思考看板), /log (全量追踪), /clear (清屏)"
		return fmt.Sprintf("\n%s\n%s\n\n", title, dimStyle.Render(text))
	}

	var sb strings.Builder
	for i, msg := range m.messages {
		switch msg.Sender {
		case "You":
			badge := userBadgeStyle.Render(" ❯ You ")
			userContent := userBlockContainer.Render(userPromptTextStyle.Render(msg.Content))
			sb.WriteString(fmt.Sprintf("%s\n%s\n\n", badge, userContent))

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

		case "Tide":
			if len(msg.Blocks) > 0 {
				var sbTide strings.Builder
				headerShown := false

				for bIdx, block := range msg.Blocks {
					switch block.Kind {
					case BlockReasoning:
						if strings.TrimSpace(block.Text) != "" {
							raw := strings.TrimSpace(block.Text)
							lines := strings.Split(raw, "\n")
							thoughtHeader := reasoningTitleStyle.Render("💭 深度思考") + " " + dimStyle.Render("[按 Ctrl+T 打开独立看板]")
							var preview string
							if len(lines) > 4 {
								preview = strings.Join(lines[:3], "\n") + "\n" + dimStyle.Render(fmt.Sprintf("... (已折叠 %d 行思考，按 Ctrl+T 展开沉浸看板)", len(lines)-3))
							} else {
								preview = raw
							}
							capsule := thinkingCapsuleStyle.Width(max(40, cardWidth-4)).Render(fmt.Sprintf("%s\n%s", thoughtHeader, reasoningTextStyle.Render(preview)))
							sbTide.WriteString(capsule + "\n\n")
						}

					case BlockTool:
						if block.Tool != nil {
							sbTide.WriteString(renderToolCard(*block.Tool, cardWidth) + "\n\n")
						}

					case BlockPermission:
						if block.Permission != nil {
							sbTide.WriteString(renderPermissionAuditCard(*block.Permission, cardWidth) + "\n\n")
						}

					case BlockText:
						if !headerShown {
							sbTide.WriteString(assistantBadgeStyle.Render(" 🌊 Tide ") + "\n\n")
							headerShown = true
						}
						var text string
						isLastBlock := bIdx == len(msg.Blocks)-1
						if m.isGenerating && i == len(m.messages)-1 && isLastBlock {
							text = renderMarkdown(block.Text, cardWidth) + cursorStyle.Render(" ▊")
						} else {
							text = renderMarkdownCached(block.Text, cardWidth)
						}
						sbTide.WriteString(text + "\n\n")
					}
				}

				if msg.Usage != nil && msg.Usage.TotalTokens > 0 {
					usageText := tokenBadgeStyle.Render(fmt.Sprintf("⚡ %d tokens (输入 %d / 输出 %d)",
						msg.Usage.TotalTokens, msg.Usage.PromptTokens, msg.Usage.CompletionTokens))
					sbTide.WriteString("  " + usageText + "\n\n")
				}

				sb.WriteString(sbTide.String())
				continue
			}

			// 若暂无结构化块
			if msg.Content != "" || (m.isGenerating && i == len(m.messages)-1) {
				header := assistantBadgeStyle.Render(" 🌊 Tide ")
				var bodyText string
				if msg.Content != "" {
					if m.isGenerating && i == len(m.messages)-1 {
						bodyText = renderMarkdown(msg.Content, cardWidth)
					} else {
						bodyText = renderMarkdownCached(msg.Content, cardWidth)
					}
				} else {
					bodyText = m.spinner.View() + dimStyle.Render(" 正在思考中...")
				}

				usageText := ""
				if msg.Usage != nil && msg.Usage.TotalTokens > 0 {
					usageText = "\n  " + tokenBadgeStyle.Render(fmt.Sprintf("⚡ %d tokens (输入 %d / 输出 %d)",
						msg.Usage.TotalTokens, msg.Usage.PromptTokens, msg.Usage.CompletionTokens))
				}

				sb.WriteString(fmt.Sprintf("%s\n\n%s%s\n\n", header, bodyText, usageText))
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
	s.WriteString(m.renderHeaderBar() + "\n")

	// 2. 中部 Viewport 聊天记录滚动展示
	if m.viewportReady {
		s.WriteString(m.viewport.View() + "\n")
	} else {
		s.WriteString(m.renderChatMessages() + "\n")
	}

	// 3. 若有挂起的权限审批，高亮呈现权限提示卡片
	if m.pendingPerm != nil {
		s.WriteString(m.renderPermissionCard() + "\n")
	}

	// 4. 底部高亮交互驾驶舱 (Command Dock: 整合输入框、模式状态、当前模型、滚动指示与按键操作)
	s.WriteString(m.renderInputBox())

	return s.String()
}

// renderToolCard 将工具调用的执行状态、输入参数及输出结果渲染为精致的 Bento 圆角卡片
func renderToolCard(tc ToolCallRecord, cardWidth int) string {
	innerW := max(36, cardWidth-4)

	var (
		cardStyle lipgloss.Style
		badge     string
	)

	if tc.Result == nil {
		cardStyle = toolCardRunningStyle
		badge = toolBadgeRunning.Render(" ⚙️ RUNNING ")
	} else if tc.Result.IsError {
		cardStyle = toolCardErrorStyle
		badge = toolBadgeError.Render(" ✖ ERROR ")
	} else {
		cardStyle = toolCardSuccessStyle
		badge = toolBadgeSuccess.Render(" ✔ SUCCESS ")
	}

	var sb strings.Builder
	// 顶部状态栏：徽章 + 工具名称与语义图标
	iconTitle := toolSemanticIcon(tc.Call.Name)
	sb.WriteString(fmt.Sprintf("%s %s\n", badge, toolHeaderStyle.Render(iconTitle)))

	// 参数区
	if tc.Call.Arguments != "" && tc.Call.Arguments != "{}" {
		sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelOrange.Render("⚡ 参数:"), codeArgStyle.Render(tc.Call.Arguments)))
	}

	// 结果输出区
	if tc.Result != nil && tc.Result.Content != "" {
		divider := dockDividerStyle.Render(strings.Repeat("─", max(20, innerW-4)))
		sb.WriteString("  " + divider + "\n")

		if tc.Result.IsError {
			errText := strings.TrimSpace(tc.Result.Content)
			sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelRed.Render("❌ 错误:"), errText))
		} else {
			snippet := strings.TrimSpace(tc.Result.Content)
			lines := strings.Split(snippet, "\n")
			if len(lines) > 5 {
				snippet = strings.Join(lines[:5], "\n") + fmt.Sprintf("\n  ... (共 %d 行，其余已折叠)", len(lines))
			} else if len(snippet) > 300 {
				snippet = textutil.TruncateUTF8(snippet, 300) + "... (已截断)"
			}
			sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelGreen.Render("📄 结果:"), snippet))
		}
	}

	return cardStyle.Width(innerW).Render(sb.String())
}

// renderPermissionAuditCard 渲染已完成审批的权限拦截历史审计存根卡片
func renderPermissionAuditCard(pr PermissionRecord, cardWidth int) string {
	innerW := max(40, cardWidth-2)

	var (
		cardStyle    lipgloss.Style
		badge        string
		decisionText string
	)

	switch pr.Decision {
	case protocol.DecisionAllowOnce:
		cardStyle = permissionAuditAllowedStyle
		badge = permissionAuditBadgeAllowed.Render(" 🛡️ 权限审批 · 已放行 ")
		decisionText = permissionAuditDecisionAllow.Render("✔ 用户决策: 允许本次执行 (单次放行)")
	case protocol.DecisionAllowSession:
		cardStyle = permissionAuditAllowedStyle
		badge = permissionAuditBadgeAllowed.Render(" 🛡️ 权限审批 · 会话信任 ")
		decisionText = permissionAuditDecisionAllow.Render("✔ 用户决策: 本会话始终信任同类命令")
	default: // DecisionDeny
		cardStyle = permissionAuditDeniedStyle
		badge = permissionAuditBadgeDenied.Render(" 🛡️ 权限审批 · 已阻断 ")
		decisionText = permissionAuditDecisionDeny.Render("✖ 用户决策: 拒绝执行并安全阻断")
	}

	var sb strings.Builder
	// 顶部凭证栏
	sb.WriteString(fmt.Sprintf("%s %s\n", badge, dimStyle.Render("Gate 3 审计存根")))

	// 详情行
	if pr.Request.ToolName != "" {
		sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelOrange.Render("⚡ 目标工具:"), pr.Request.ToolName))
	}
	if pr.Request.Arguments != "" {
		sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelCyan.Render("📝 风险调用:"), codeArgStyle.Render(pr.Request.Arguments)))
	}
	if pr.Request.Reason != "" {
		sb.WriteString(fmt.Sprintf("  %s %s\n", cardLabelRed.Render("⚠️  拦截原因:"), pr.Request.Reason))
	}

	divider := dockDividerStyle.Render(strings.Repeat("─", max(20, innerW-4)))
	sb.WriteString("  " + divider + "\n")
	sb.WriteString("  " + decisionText)

	return cardStyle.Width(innerW).Render(sb.String())
}
