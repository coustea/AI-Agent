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
	// 组装调用链：LLM -> Gateway -> Agent (驱动 ReAct 循环与内置工具) -> TUI
	// 配置文件损坏时回退全新默认装配；未就绪状态由 ConfigView 表达，交由 /model 向导修复
	cfg, err := config.LoadConfig("")
	if err != nil {
		cfg = config.DefaultConfig()
	}

	ag, err := agent.NewFromConfig(cfg)
	if err != nil {
		// 配置语义无效（如未知厂商）时同样回退，保证前端始终获得可注入的内核
		ag, err = agent.NewFromConfig(config.DefaultConfig())
	}
	if err != nil {
		fmt.Printf("coustea 内核装配失败: %v\n", err)
		os.Exit(1)
	}

	// 启动 TUI 终端界面，注入解耦后的 agent 实例
	m := tui.NewModel(ag)

	p := tea.NewProgram(m)
	if _, err := p.Run(); err != nil {
		fmt.Printf("coustea 运行异常: %v\n", err)
		os.Exit(1)
	}
}
