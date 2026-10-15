package tui

import (
	"context"
	"fmt"
	"os"
	"strings"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/gateway"

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
				// 切换到模型配置向导页面
				m.state = stateSelectModel
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
			case "/exit", "/quit":
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
			m.chatInput.Placeholder = "coustea 正在思考生成中..."

			// 3. 如果注入了 Agent 内核接口，开启流式会话；若未注入尝试按配置动态连接
			if m.bridge == nil && (m.config.APIKey != "" || config.IsLocalProvider(m.config.Provider)) {
				if gw, err := gateway.NewGatewayFromConfig(&m.config); err == nil {
					if ag, err := agent.NewAgent(gw, agent.WithDefaultTools()); err == nil {
						m.bridge = ag
					}
				}
			}

			if m.bridge != nil {
				ch, err := m.bridge.StreamRun(context.Background(), text)
				if err != nil {
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

	// 3. 底部输入框（Claude Code 质感输入）
	s.WriteString(m.chatInput.View() + "\n\n")

	// 4. 底部快捷栏提示
	s.WriteString(footerStyle.Render("快捷操作: [Enter] 发送  [/model] 更换模型  [/clear] 清屏  [Ctrl+C] 退出") + "\n")

	return s.String()
}
