package main

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"

	"my-agent/internal/agent"
	"my-agent/internal/config"
	"my-agent/internal/middleware"
	"my-agent/internal/tui"

	tea "github.com/charmbracelet/bubbletea"
)

func printHelp() {
	fmt.Printf(`tide - 本地终端通用 AI 个人助手 (ReAct + Harness)

版本:
  %s (%s/%s)

用法:
  tide                启动交互式终端全屏界面 (TUI)
  tide update         检查并一键平滑升级至最新版本
  tide --version, -v  显示当前版本信息
  tide --help, -h     显示命令行帮助信息

快捷指令 (在 TUI 中使用):
  /model              切换模型平台与配置 API Key
  /think              打开深度思考过程独立看板 (或按 Ctrl+T)
  /log                打开全量调用链路与 JSON 追踪看板 (或按 Ctrl+L)
  /update             查看最新版本更新方法
  /clear              清空当前屏幕对话
  /exit, /quit        退出程序 (或按 Ctrl+C / Ctrl+D)

更多信息与文档:
  https://github.com/coustea/AI-Agent
`, config.Version, runtime.GOOS, runtime.GOARCH)
}

func executeUpdate() {
	fmt.Printf("🌊 正在更新 Tide (当前版本 %s)...\n", config.Version)
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("powershell", "-NoProfile", "-Command", "irm https://raw.githubusercontent.com/coustea/AI-Agent/my-agent/install.ps1 | iex")
	} else {
		cmd = exec.Command("sh", "-c", "curl -fsSL https://raw.githubusercontent.com/coustea/AI-Agent/my-agent/install.sh | bash")
	}
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		fmt.Printf("更新失败: %v\n如遇网络问题，请访问 https://github.com/coustea/AI-Agent/releases 手动下载最新版本。\n", err)
		os.Exit(1)
	}
}

func main() {
	for _, arg := range os.Args[1:] {
		switch arg {
		case "-v", "--version", "version":
			fmt.Printf("tide %s (%s/%s)\n", config.Version, runtime.GOOS, runtime.GOARCH)
			return
		case "-h", "--help", "help":
			printHelp()
			return
		case "update", "--update", "upgrade":
			executeUpdate()
			return
		}
	}
	// 组装调用链：LLM -> Gateway -> Agent (驱动 ReAct 循环与内置工具) -> TUI
	// 配置文件损坏时回退全新默认装配；未就绪状态由 ConfigView 表达，交由 /model 向导修复
	cfg, err := config.LoadConfig("")
	if err != nil {
		cfg = config.DefaultConfig()
	}

	// 可替换策略（日志审计、大结果落盘）由宿主显式装配，内核只保留挂载机制
	wd, _ := os.Getwd()
	traceLogger := middleware.NewLoggingMiddleware(wd)
	opts := []agent.Option{
		agent.WithHook(traceLogger),
		agent.WithPostToolUse(middleware.LargeResultSpill(wd)),
	}

	ag, err := agent.NewFromConfig(cfg, opts...)
	if err != nil {
		// 配置语义无效（如未知厂商）时同样回退，保证前端始终获得可注入的内核
		ag, err = agent.NewFromConfig(config.DefaultConfig(), opts...)
	}
	if err != nil {
		fmt.Printf("tide 内核装配失败: %v\n", err)
		os.Exit(1)
	}

	// 启动 TUI 终端界面，注入解耦后的 agent 实例与追踪数据源
	m := tui.NewModel(ag, traceLogger)

	p := tea.NewProgram(m, tea.WithMouseCellMotion(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Printf("tide 运行异常: %v\n", err)
		os.Exit(1)
	}
}
