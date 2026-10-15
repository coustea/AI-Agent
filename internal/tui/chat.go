package tui

import (
	"context"
	"fmt"
	"os"
	"strings"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/gateway"
	"my-agent/internal/memory"
	"my-agent/internal/permission"

	tea "github.com/charmbracelet/bubbletea"
)

// ToolCallRecord 结构化记录单次工具调用过程与结果
type ToolCallRecord struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
	Result    string `json:"result,omitempty"`
	IsError   bool   `json:"is_error,omitempty"`
	Running   bool   `json:"running,omitempty"`
}

// ChatMessage 用于在界面上展示发送和接收的消息
type ChatMessage struct {
	Sender           string           // "You", "coustea", "System"
	Content          string           // 最终回复文本
	ReasoningContent string           // 深度思考链 (DeepSeek 等)
	ToolCalls        []ToolCallRecord // 结构化工具调用列表
	Usage            *gateway.Usage   // 携带的 Token 用量统计（可选）
}

// updateChat 处理聊天页面的键盘输入和发送逻辑
func (m Model) updateChat(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		// 1. 若当前存在挂起的权限审批请求，优先处理审批交互
		if m.pendingPrompt != nil {
			switch msg.String() {
			case "y", "Y":
				m.pendingPrompt.Respond(permission.DecisionAllowOnce)
				m.pendingPrompt = nil
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			case "a", "A":
				m.pendingPrompt.Respond(permission.DecisionAllowSession)
				m.pendingPrompt = nil
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			case "n", "N":
				m.pendingPrompt.Respond(permission.DecisionDeny)
				m.pendingPrompt = nil
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil
			}

			if msg.Type == tea.KeyEsc {
				m.pendingPrompt.Respond(permission.DecisionDeny)
				m.pendingPrompt = nil
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

			// 处理快捷命令
			switch text {
			case "/model", "/config":
				m.state = stateSelectModel
				m.cursor = m.selected
				m.chatInput.Reset()
				return m, nil

			case "/clear":
				m.messages = nil
				m.chatInput.Reset()
				if m.bridge != nil {
					m.bridge.Reset()
				}
				if m.viewportReady {
					m.viewport.SetContent(m.renderChatMessages())
					m.viewport.GotoBottom()
				}
				return m, nil

			case "/exit", "/quit", "/q":
				return m, tea.Quit
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

			// 如果注入了 Agent 内核接口，开启流式会话；若未注入尝试按配置动态连接
			if m.bridge == nil && (m.config.APIKey != "" || config.IsLocalProvider(m.config.Provider)) {
				if gw, err := gateway.NewGatewayFromConfig(&m.config); err == nil {
					if ag, err := agent.NewAgent(gw, agent.WithDefaultTools()); err == nil {
						m.bridge = ag
					}
				}
			}

			if m.bridge != nil {
				ctx, cancel := context.WithCancel(context.Background())
				m.cancel = cancel
				ch, err := m.bridge.StreamRun(ctx, text)
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

			// 若仍然无法建立连接（例如缺少 APIKey）
			m.messages[len(m.messages)-1].Content = "[未配置可用模型] 请先输入 /model 配置 API Key 或设置环境变量 (DEEPSEEK_API_KEY / GEMINI_API_KEY)。"
			m.isGenerating = false
			m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
			if m.viewportReady {
				m.viewport.SetContent(m.renderChatMessages())
				m.viewport.GotoBottom()
			}
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.chatInput, cmd = m.chatInput.Update(msg)
	return m, cmd
}

// renderHeaderBar 渲染固定在顶部的 Claude 风格品牌与状态栏
func (m Model) renderHeaderBar() string {
	var sb strings.Builder
	cwd, _ := os.Getwd()

	modelInfo := "未配置模型 (输入 /model 配置)"
	if m.config.ModelName != "" {
		modelInfo = fmt.Sprintf("%s • %s", m.config.Provider, m.config.ModelName)
	}

	brandBadge := headerBadgeStyle.Render(" coustea ")
	modelTag := headerTagStyle.Render(modelInfo)

	// 计算长效记忆激活篇数
	bundle := memory.LoadBundle(cwd)
	memCount := len(bundle.GlobalFiles) + len(bundle.ProjectFiles)
	memTag := headerMemoryStyle.Render(fmt.Sprintf("🧠 %d 篇记忆生效", memCount))

	dirTag := headerDirStyle.Render(" 目录: " + cwd)

	headerRow := fmt.Sprintf("%s %s %s%s", brandBadge, modelTag, memTag, dirTag)
	sb.WriteString("\n" + headerRow + "\n")

	divider := headerDividerStyle.Render(strings.Repeat("─", max(50, m.width-2)))
	sb.WriteString(divider)
	return sb.String()
}

// renderStatusBar 渲染运行状态指示器 (Spinner + 就绪/思考/工具中 + 视口滚动百分比)
func (m Model) renderStatusBar() string {
	var statusText string
	if m.pendingPrompt != nil {
		statusText = permissionWarnStyle.Render("🛡️ 等待授权审批 (Gate 3)")
	} else if m.activeToolName != "" {
		statusText = toolRunningStyle.Render(fmt.Sprintf("%s 正在执行工具 [%s]...", m.spinner.View(), m.activeToolName))
	} else if m.isGenerating {
		statusText = statusThinkingStyle.Render(fmt.Sprintf("%s 正在思考生成中...", m.spinner.View()))
	} else {
		statusText = statusReadyStyle.Render("● 就绪")
	}

	scrollHint := ""
	if m.viewportReady && m.viewport.TotalLineCount() > m.viewport.Height {
		percent := int(m.viewport.ScrollPercent() * 100)
		scrollHint = scrollIndicatorStyle.Render(fmt.Sprintf(" [已滚至 %d%% | PgUp/PgDn 滚动]", percent))
	}

	return fmt.Sprintf(" %s%s\n", statusText, scrollHint)
}

// renderChatMessages 将所有历史消息格式化为适用于 Viewport 渲染的高质量文本
func (m Model) renderChatMessages() string {
	if len(m.messages) == 0 {
		return dimStyle.Render("  [欢迎使用 coustea 智能助手] 在下方输入消息按 Enter 开始对话。\n  随时输入 /model 切换模型平台，输入 /clear 可清空上下文记忆。\n")
	}

	var sb strings.Builder
	for i, msg := range m.messages {
		switch msg.Sender {
		case "You":
			sb.WriteString(userPrefixStyle.Render("❯ You: ") + msg.Content + "\n\n")

		case "System":
			sb.WriteString(systemPrefixStyle.Render("● System: ") + dimStyle.Render(msg.Content) + "\n\n")

		case "coustea":
			// 1. 若有深度思考链，独立渲染高雅的思考过程折叠块
			if msg.ReasoningContent != "" {
				sb.WriteString(reasoningTitleStyle.Render("💭 思考过程 (Thinking Process):") + "\n")
				sb.WriteString(reasoningBoxStyle.Render(msg.ReasoningContent) + "\n\n")
			}

			// 2. 若有工具调用，按结构化卡片渲染
			for _, tc := range msg.ToolCalls {
				var card strings.Builder
				if tc.Running {
					card.WriteString(fmt.Sprintf("%s %s\n", toolRunningStyle.Render("⏳ 正在调用工具:"), toolHeaderStyle.Render(tc.Name)))
				} else if tc.IsError {
					card.WriteString(fmt.Sprintf("%s %s\n", toolResultErrorStyle.Render("✖ 工具执行报错:"), toolHeaderStyle.Render(tc.Name)))
				} else {
					card.WriteString(fmt.Sprintf("%s %s\n", toolResultSuccessStyle.Render("✔ 工具执行完成:"), toolHeaderStyle.Render(tc.Name)))
				}

				if tc.Arguments != "" && tc.Arguments != "{}" {
					card.WriteString(fmt.Sprintf("  ↳ %s\n", toolSnippetStyle.Render("参数: "+tc.Arguments)))
				}
				if tc.Result != "" {
					snippet := strings.TrimSpace(tc.Result)
					lines := strings.Split(snippet, "\n")
					if len(lines) > 4 {
						snippet = strings.Join(lines[:4], "\n") + fmt.Sprintf("\n  ... (共 %d 行，其余已折叠)", len(lines))
					} else if len(snippet) > 240 {
						snippet = snippet[:240] + "... (已截断)"
					}
					card.WriteString(fmt.Sprintf("  ↳ %s\n", toolSnippetStyle.Render("结果: "+snippet)))
				}
				sb.WriteString(toolCardBoxStyle.Render(card.String()) + "\n\n")
			}

			// 3. 最终回复文本
			if msg.Content != "" {
				sb.WriteString(assistantPrefixStyle.Render("● coustea:\n") + msg.Content + "\n")
			} else if m.isGenerating && i == len(m.messages)-1 && len(msg.ToolCalls) == 0 && msg.ReasoningContent == "" {
				sb.WriteString(assistantPrefixStyle.Render("● coustea: ") + m.spinner.View() + dimStyle.Render(" 正在思考中...\n"))
			}

			// 4. Token 用量
			if msg.Usage != nil && msg.Usage.TotalTokens > 0 {
				usageText := fmt.Sprintf("  ↳ Token 用量: %d (输入 %d / 输出 %d)",
					msg.Usage.TotalTokens, msg.Usage.PromptTokens, msg.Usage.CompletionTokens)
				sb.WriteString(dimStyle.Render(usageText) + "\n")
			}
			sb.WriteString("\n")

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

	// 3. 运行状态栏 (就绪/思考中/工具执行中)
	s.WriteString(m.renderStatusBar())

	// 4. 若有挂起的权限审批，高亮呈现权限提示卡片
	if m.pendingPrompt != nil {
		req := m.pendingPrompt.Request
		permCard := fmt.Sprintf("⚠ [权限审批 Gate 3] 工具 [%s] 尝试执行\n参数: %s\n原因: %s\n\n操作: [y] 允许本次  [a] 本会话始终允许  [n/Esc] 拒绝本次",
			req.ToolName, string(req.Arguments), req.Reason)
		s.WriteString(permissionBoxStyle.Render(permCard) + "\n\n")
	}

	// 5. 底部输入框（Claude Code 质感输入）
	s.WriteString(m.chatInput.View() + "\n\n")

	// 6. 底部快捷栏提示
	if m.pendingPrompt != nil {
		s.WriteString(permissionWarnStyle.Render("等待权限审批: 按 [y] 允许本次  [a] 本会话始终允许  [n/Esc] 拒绝本次  [Ctrl+C] 退出") + "\n")
	} else {
		s.WriteString(footerStyle.Render("快捷操作: [Enter] 发送  [PgUp/PgDn] 滚动历史  [/model] 更换模型  [/clear] 清屏  [Ctrl+C] 退出") + "\n")
	}

	return s.String()
}
