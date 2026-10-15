package main

import (
	"fmt"
	"os"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/gateway"
	"my-agent/internal/tui"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	var bridge tui.AgentBridge

	// 组装调用链：LLM -> Gateway -> Agent (驱动 ReAct 循环与内置工具) -> TUI
	cfg, err := config.LoadConfig("")
	if err == nil && cfg != nil && (cfg.APIKey != "" || config.IsLocalProvider(cfg.Provider)) {
		if gw, err := gateway.NewGatewayFromConfig(cfg); err == nil {
			if ag, err := agent.NewAgent(gw, agent.WithDefaultTools()); err == nil {
				bridge = ag
			}
		}
	}

	// 启动 TUI 终端界面，注入解耦的 bridge
	m := tui.NewModel(bridge)

	p := tea.NewProgram(m)
	if _, err := p.Run(); err != nil {
		fmt.Printf("coustea 运行异常: %v\n", err)
		os.Exit(1)
	}
}
