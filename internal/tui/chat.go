package tui

import (
	"context"
	"fmt"
	"os"
	"strings"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/gateway"
	"my-agent/internal/permission"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ChatMessage 用于在界面上展示发送和接收的消息
type ChatMessage struct {
	Sender  string         // "You", "coustea", "System"
	Content string         // 消息文本
	Usage   *gateway.Usage // 携带的 Token 用量统计（可选）
}

// updateChat 处理聊天页面的键盘输入和发送逻辑
func (m Model) updateChat(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		// 若当前存在挂起的权限审批请求，优先处理审批交互
		if m.pendingPrompt != nil {
			switch msg.String() {
			case "y", "Y":
				m.pendingPrompt.Respond(permission.DecisionAllowOnce)
				m.pendingPrompt = nil
				return m, nil
			case "a", "A":
				m.pendingPrompt.Respond(permission.DecisionAllowSession)
				m.pendingPrompt = nil
				return m, nil
			case "n", "N":
				m.pendingPrompt.Respond(permission.DecisionDeny)
				m.pendingPrompt = nil
				return m, nil
			}

			if msg.Type == tea.KeyEsc {
				m.pendingPrompt.Respond(permission.DecisionDeny)
				m.pendingPrompt = nil
				return m, nil
			}

			// 处于权限审批等待状态时，屏蔽其他输入
			return m, nil
		}

		switch msg.Type {
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
				// 切换到模型配置向导页面，光标对准当前激活的模型
				m.state = stateSelectModel
				m.cursor = m.selected
				m.chatInput.Reset()
				return m, nil
			case "/clear":
				// 清屏并清空 Agent 上下文记忆
				m.messages = nil
				m.chatInput.Reset()
				if m.bridge != nil {
					m.bridge.Reset()
				}
				return m, nil
			case "/exit", "/quit", "/q":
				return m, tea.Quit
			}

			// 1. 发送消息展示：将用户输入添加到消息历史
			m.messages = append(m.messages, ChatMessage{
				Sender:  "You",
				Content: text,
			})
			m.chatInput.Reset()

			// 2. 预备一条 Assistant 消息占位，等待流式增量填入
			m.messages = append(m.messages, ChatMessage{
				Sender:  "coustea",
				Content: "",
			})
			m.isGenerating = true
			m.chatInput.Placeholder = "coustea 正在思考生成中... (按 Ctrl+C 或 Esc 可中断)"

			// 3. 如果注入了 Agent 内核接口，开启流式会话；若未注入尝试按配置动态连接
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
					return m, nil
				}
				// 返回异步监听命令，启动流式打字流水线
				return m, waitForAgentEvent(ch)
			}

			// 若仍然无法建立连接（例如缺少 APIKey）
			m.messages[len(m.messages)-1].Content = "[未配置可用模型] 请先输入 /model 配置 API Key 或设置环境变量 (DEEPSEEK_API_KEY / GEMINI_API_KEY)。"
			m.isGenerating = false
			m.chatInput.Placeholder = "输入消息与 coustea 对话... (输入 /model 切换模型, /clear 清屏)"
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.chatInput, cmd = m.chatInput.Update(msg)
	return m, cmd
}

// viewChat 渲染 Claude Code 风格的主聊天页面
func (m Model) viewChat() string {
	var s strings.Builder

	cwd, _ := os.Getwd()

	// 1. Claude Code 风格顶部状态卡片
	modelInfo := "未配置模型 (输入 /model 配置)"
	if m.config.ModelName != "" {
		modelInfo = fmt.Sprintf("%s (%s)", m.config.Provider, m.config.ModelName)
	}
	headerText := fmt.Sprintf(" coustea • %s ", modelInfo)
	badge := badgeStyle.Render(headerText)
	dirInfo := dimStyle.Render(" 目录: " + cwd)

	border := lipgloss.NewStyle().Foreground(colorCoral).Render("──────────────────────────────────────────────────────────────────────")

	s.WriteString("\n" + badge + dirInfo + "\n")
	s.WriteString(border + "\n\n")

	// 2. 消息展示区
	if len(m.messages) == 0 {
		s.WriteString(dimStyle.Render("  [欢迎使用 coustea] 在下方输入消息并按回车发送。输入 /model 重新配置模型。\n\n"))
	} else {
		for _, msg := range m.messages {
			switch msg.Sender {
			case "You":
				prefix := userPrefixStyle.Render("❯ You: ")
				s.WriteString(prefix + msg.Content + "\n\n")
			case "System":
				prefix := dimStyle.Render("● System: ")
				s.WriteString(prefix + dimStyle.Render(msg.Content) + "\n\n")
			case "coustea":
				prefix := assistantPrefixStyle.Render("● coustea: ")
				content := msg.Content
				if content == "" && m.isGenerating {
					content = dimStyle.Render("▰▰▰ 思考中...")
				}
				s.WriteString(prefix + content + "\n")
				// 若有 Token 用量数据，展示在下方
				if msg.Usage != nil && msg.Usage.TotalTokens > 0 {
					usageText := fmt.Sprintf("  ↳ Token 用量: %d (输入 %d / 输出 %d)",
						msg.Usage.TotalTokens, msg.Usage.PromptTokens, msg.Usage.CompletionTokens)
					s.WriteString(dimStyle.Render(usageText) + "\n")
				}
				s.WriteString("\n")
			default:
				s.WriteString(fmt.Sprintf("%s: %s\n\n", msg.Sender, msg.Content))
			}
		}
	}

	// 3. 若有挂起的权限审批，高亮呈现权限提示卡片
	if m.pendingPrompt != nil {
		req := m.pendingPrompt.Request
		permCard := fmt.Sprintf("⚠ [权限审批 Gate 3] 工具 [%s] 尝试执行\n参数: %s\n原因: %s\n\n操作: [y] 允许本次  [a] 本会话始终允许  [n/Esc] 拒绝本次",
			req.ToolName, string(req.Arguments), req.Reason)
		s.WriteString(permissionBoxStyle.Render(permCard) + "\n\n")
	}

	// 4. 底部输入框（Claude Code 质感输入）
	s.WriteString(m.chatInput.View() + "\n\n")

	// 5. 底部快捷栏提示
	if m.pendingPrompt != nil {
		s.WriteString(permissionWarnStyle.Render("等待权限审批: 按 [y] 允许本次  [a] 本会话始终允许  [n/Esc] 拒绝本次  [Ctrl+C] 退出") + "\n")
	} else {
		s.WriteString(footerStyle.Render("快捷操作: [Enter] 发送  [/model] 更换模型  [/clear] 清屏  [Ctrl+C] 退出") + "\n")
	}

	return s.String()
}
