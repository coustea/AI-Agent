// Package agent 的隔离型子代理声明式装配（explorer / worker）。
//
// 设计原则：
//   - 子代理共享底层 ChatModel 连接与 toolGuard，但各自持有独立的 tokenBudget 与 reduction 管线，
//     避免子代理的大量中间检索/脚本输出污染主代理上下文；
//   - 子代理统一关闭思考模式（ThinkingDisabled），并收紧迭代次数与单次输出上限，防止长耗散；
//   - explorer 严格只读（禁用 write/edit/execute）；worker 允许小步写文件与命令校验，不授予外部检索工具。
package agent

import (
	"context"
	"fmt"
	"strings"

	"github.com/cloudwego/eino/adk"
	adkfs "github.com/cloudwego/eino/adk/filesystem"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
)

const (
	subAgentExplorer        = "explorer"
	subAgentWorker          = "worker"
	explorerMaxIterations   = 6
	explorerMaxOutputTokens = 8192
	workerMaxIterations     = 10
	workerMaxOutputTokens   = 16384
)

const explorerInstruction = `<identity>
你是只读资料与工作区检索子代理（explorer），负责在独立上下文中收集信息并向主代理返回精炼摘要。
</identity>
<rules>
- 优先用 ls / glob / grep 定位工作区文件，再用 read_file 分段读取（单次上限 200 行，禁止对目录调用 read_file）或用 read_attachment 分页核对。
- web_search 仅返回网页摘要片段，系统不支持抓取完整网页或远程源码；联网搜索最多 2~3 轮，摘要未包含的精确函数签名或细节如实标注“公开检索摘要未包含”并立即收敛，严禁反复换词死搜。
- 严格只读，不修改任何文件；所有结论附带具体文件路径、行号或来源链接，只输出结构化精炼结论。
</rules>`

const workerInstruction = `<identity>
你是工作区小步执行与校验子代理（worker），负责在独立上下文中完成主代理委派的单个边界清晰的写入、修改、运行或校验子任务。
</identity>
<rules>
- 严格遵循工具契约：写文件小步模块化（单次上限 220 行 / 12 KB），已有文件优先 edit_file 局部修改；/skills 目录严格只读。
- 命令在工作区目录执行，读完报错再修，不盲目重复同一失败命令。
- 完成后只返回简明执行报告：产出/修改的文件路径、大小、命令校验结果及遗留问题。
</rules>`

// subAgentSpec 声明式描述一个受控子代理的能力边界与资源配额。
type subAgentSpec struct {
	name          string
	description   string
	instruction   string
	maxIterations int
	maxOutput     int
	readOnly      bool
	tools         []tool.BaseTool
}

// newSubAgents 按声明式规格构建全部子代理；中间件顺序与主代理保持同构：
// guard -> filesystem -> reduction -> budget -> noThink。
func newSubAgents(
	ctx context.Context,
	cm model.ToolCallingChatModel,
	backend adkfs.Backend,
	shell adkfs.Shell,
	readOnlyTools []tool.BaseTool,
	cfg Config,
	guard adk.ChatModelAgentMiddleware,
) ([]adk.Agent, error) {
	noThink := newThinking(thinkingDisabled, cfg.ModelProvider, cfg.ModelExtra)

	specs := []subAgentSpec{
		{
			name:          subAgentExplorer,
			description:   "只读资料与工作区检索助手：在独立上下文中排查多个工作区文件、分段精读长附件或多主题检索并返回精炼摘要（不支持抓取完整网页）。",
			instruction:   explorerInstruction,
			maxIterations: explorerMaxIterations,
			maxOutput:     explorerMaxOutputTokens,
			readOnly:      true,
			tools:         readOnlyTools,
		},
		{
			name:          subAgentWorker,
			description:   "工作区小步执行与校验助手：在独立上下文中编写单个独立模块文件、局部修改代码、执行构建/校验脚本并汇报结果。",
			instruction:   workerInstruction,
			maxIterations: workerMaxIterations,
			maxOutput:     workerMaxOutputTokens,
			readOnly:      false,
		},
	}

	subs := make([]adk.Agent, 0, len(specs))
	for _, spec := range specs {
		fsMW, err := newFilesystemMiddleware(ctx, backend, shell, spec.readOnly)
		if err != nil {
			return nil, err
		}
		budget := newTokenBudget(cfg.ContextWindow, min(cfg.MaxToken, spec.maxOutput), spec.name)
		reduceMW, err := newReductionMiddleware(ctx, budget)
		if err != nil {
			return nil, err
		}
		sub, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
			Name:          spec.name,
			Description:   spec.description,
			Instruction:   spec.instruction,
			Model:         cm,
			MaxIterations: spec.maxIterations,
			ToolsConfig: adk.ToolsConfig{
				ToolsNodeConfig: compose.ToolsNodeConfig{
					Tools:               spec.tools,
					UnknownToolsHandler: unknownToolHandler,
				},
			},
			Handlers: []adk.ChatModelAgentMiddleware{guard, fsMW, reduceMW, budget, noThink},
		})
		if err != nil {
			return nil, fmt.Errorf("构建 %s 子代理失败: %w", spec.name, err)
		}
		subs = append(subs, sub)
	}
	return subs, nil
}

// taskToolDescription 供 Eino DeepAgent 生成 task 工具描述，参数协议仍沿用官方定义。
func taskToolDescription(ctx context.Context, subs []adk.Agent) (string, error) {
	var sb strings.Builder
	sb.WriteString("在独立隔离上下文中委派子代理完成子任务，仅返回精炼结果以减少主对话上下文消耗。\n\n可用子代理（subagent_type）：\n")
	for _, a := range subs {
		fmt.Fprintf(&sb, "- %s：%s\n", a.Name(ctx), a.Description(ctx))
	}
	sb.WriteString("\n传参要求：description 必须自包含目标、涉及路径和期望返回格式；子代理看不到主对话历史，且无权访问完整网页原文。")
	return sb.String(), nil
}
