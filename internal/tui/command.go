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

	// 2. 模型配置与切换类指令 (解耦委托给 model.go 处理)
	if trimmed == "/model" || trimmed == "/config" {
		newM, cmd := m.handleModelCommand("")
		return newM, cmd, true
	}
	if strings.HasPrefix(trimmed, "/model ") || strings.HasPrefix(trimmed, "/config ") {
		arg := strings.TrimSpace(strings.TrimPrefix(strings.TrimPrefix(trimmed, "/model "), "/config "))
		newM, cmd := m.handleModelCommand(arg)
		return newM, cmd, true
	}

	return m, nil, false
}
