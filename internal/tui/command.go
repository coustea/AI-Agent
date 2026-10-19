package tui

import (
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// handleSlashCommand 统一拦截并分发以 "/" 开头的终端快捷指令
// 返回值: (更新后的 Model, 执行命令 tea.Cmd, 是否成功处理了指令 handled)
func (m Model) handleSlashCommand(text string) (Model, tea.Cmd, bool) {
	if !strings.HasPrefix(text, "/") {
		return m, nil, false
	}

	trimmed := strings.TrimSpace(text)

	// 1. 系统控制类指令
	switch trimmed {
	case "/exit", "/quit", "/q":
		m.shutdown()
		return m, tea.Quit, true

	case "/clear":
		m.messages = nil
		m.chatInput.Reset()
		m.agent.Reset()
		if m.viewportReady {
			m.viewport.SetContent(m.renderChatMessages())
			m.viewport.GotoBottom()
		}
		return m, nil, true
	}

	// 2. 模型配置与切换类指令 (解耦委托给 config_wizard.go 处理)
	if trimmed == "/model" || trimmed == "/config" {
		newM, cmd := m.handleModelCommand("")
		return newM, cmd, true
	}
	if strings.HasPrefix(trimmed, "/model ") || strings.HasPrefix(trimmed, "/config ") {
		parts := strings.SplitN(trimmed, " ", 2)
		arg := ""
		if len(parts) > 1 {
			arg = strings.TrimSpace(parts[1])
		}
		newM, cmd := m.handleModelCommand(arg)
		return newM, cmd, true
	}

	// 3. 全系统结构化 JSON 追踪审计看板指令
	if trimmed == "/log" || trimmed == "/trace" {
		m.chatInput.Reset()
		newM := m.openTraceInspector()
		return newM, nil, true
	}

	// 4. 深度思考过程沉浸看板指令
	if trimmed == "/think" || trimmed == "/thinking" || trimmed == "/reasoning" || trimmed == "/cot" {
		m.chatInput.Reset()
		newM := m.openThinkingViewer()
		return newM, nil, true
	}

	// 5. 版本更新提示指令
	if trimmed == "/update" || trimmed == "/upgrade" {
		m.chatInput.Reset()
		m.messages = append(m.messages, ChatMessage{
			Sender:  "Tide",
			Content: "💡 **如何更新 Tide 至最新版本：**\n\n- **终端一键更新**：退出当前会话后在终端执行：\n  ```bash\n  tide update\n  ```\n- **重新执行一键安装**：\n  ```bash\n  curl -fsSL https://raw.githubusercontent.com/coustea/AI-Agent/my-agent/install.sh | bash\n  ```\n\n*提示：升级将平滑覆盖二进制，您的长期记忆、聊天追踪与个人配置（`~/.tide/`）均会被完好保留。*",
		})
		if m.viewportReady {
			m.viewport.SetContent(m.renderChatMessages())
			m.viewport.GotoBottom()
		}
		return m, nil, true
	}

	return m, nil, false
}
