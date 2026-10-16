package main

import (
	"fmt"
	"os"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/tui"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	var ag agent.Agent

	// 组装调用链：LLM -> Gateway -> Agent (驱动 ReAct 循环与内置工具) -> TUI
	cfg, err := config.LoadConfig("")
	if err == nil && cfg != nil && (cfg.APIKey != "" || config.IsLocalProvider(cfg.Provider)) {
		if coreAg, err := agent.NewFromConfig(cfg); err == nil {
			ag = coreAg
		}
	}

	// 启动 TUI 终端界面，注入解耦后的 agent 实例
	m := tui.NewModel(ag)

	p := tea.NewProgram(m)
	if _, err := p.Run(); err != nil {
		fmt.Printf("coustea 运行异常: %v\n", err)
		os.Exit(1)
	}
}
