// Package agent 基于 CloudWeGo Eino DeepAgent 实现 Mentorly 的单主代理（TutorAgent）与隔离型子代理协作体系。
//
// 整体分层与依赖方向（单包内聚，对外仅暴露稳定装配与运行入口）：
//   - model.go            模型构建与 SSE 分片空闲超时传输层
//   - agent.go            TutorAgent 装配、中间件管线顺序、Prompt 与空响应重试策略
//   - subagents.go        只读检索（explorer）与小步执行（worker）子代理声明式装配
//   - runtime.go          SSE 展示协议、Principal 身份边界、状态与错误映射
//   - stream.go           Run() 入口、runSession 流式事件消费状态机与回调日志
//   - harness.go          单轮运行前上下文装配（检查点 + 增量历史 + 附件引用 + 工作区概览）
//   - workspace.go        零信任虚拟文件系统（/workspace 读写、/skills 只读、软链接防逃逸）
//   - mw_*.go             5 个自研中间件（toolGuard / tokenBudget / compaction / thinking / todo）
//   - tool_*.go           3 类业务工具与执行后端（attachments / shell / web_search）
//
// 中间件洋葱执行顺序（不可随意调换）：
//  1. toolGuard      — 工具入口外层：预检 execute 高危命令与只读技能写入、约束 task 子超时、将可恢复工具错误转为模型反馈
//  2. filesystem     — 注册 ls/read_file/write_file/edit_file/grep/glob 及可选 execute
//  3. skill          — 注册只读 skill 工具，按需加载 /skills 正文
//  4. patchtoolcalls — 补齐历史中断遗留的孤立工具调用，保证后续裁剪/摘要看到合法调用对
//  5. reduction      — 50% 窗口水位线清理旧工具输出，常规轮次保留多步工作记忆与前缀缓存
//  6. todo           — 注册 write_todos，并在存在未完成项且连续 3 步未更新时追加提醒
//  7. tokenBudget    — 捕获 state.ToolInfos，并在实际调用前收紧 max_tokens、响应后单向校准与记账
//  8. compaction     — 剩余上下文达窗口 80% 时触发单轮唯一一次原子摘要，验收标准 <= 20%
//  9. thinking       — 最内层模型包装：按模式向支持的供应商注入思考开关（首调开启/后续关闭）
package agent

import (
	"cmp"
	"context"
	_ "embed"
	"fmt"
	"runtime"
	"strings"
	"time"

	"github.com/cloudwego/eino/adk"
	adkfs "github.com/cloudwego/eino/adk/filesystem"
	fsMiddleware "github.com/cloudwego/eino/adk/middlewares/filesystem"
	"github.com/cloudwego/eino/adk/middlewares/patchtoolcalls"
	"github.com/cloudwego/eino/adk/middlewares/reduction"
	"github.com/cloudwego/eino/adk/middlewares/skill"
	"github.com/cloudwego/eino/adk/prebuilt/deep"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"

	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
	logutil "mentorly/internal/utils/log"
)

const (
	AgentName           = "tutor"
	AgentDescription    = "通用学习智能体：讲解知识、分析附件、联网检索，并能自主创作文档、图解、课件与讲解视频"
	DefaultWorkspaceDir = "workspace/chat"
	DefaultSkillsDir    = "internal/agent/skills"

	defaultTaskTimeout = 120 * time.Second
	minRetryRemaining  = 2 * time.Second
)

//go:embed prompt.md
var basePrompt string

// 文件工具契约说明：引导模型小步读写；硬限制由 workspace Backend 强制执行。
var (
	readFileDesc  = "按行分页读取文件内容（路径必须为 /workspace/... 或 /skills/...）。单次最多返回 200 行；大文件请先用 grep 定位，再传 offset 与 limit 分段读取。"
	writeFileDesc = "新建或覆写 /workspace 下的文件。单次写入上限 220 行 / 12 KB；大文件或长脚本请拆分为多个小模块文件，或先写骨架再通过 edit_file 分段补充。"
	editFileDesc  = "对 /workspace 下已有文件做精确局部替换或分段追加。优先用小粒度 edit_file 修改既有文件，避免整文件重写。"
	grepDesc      = "在 /workspace 或 /skills 下按正则检索匹配行或文件路径（最多返回 200 条）。阅读大文件前优先用 grep 定位目标行号。"
)

// Config 汇总主代理与子代理共享的运行期策略配置。
type Config struct {
	ModelProvider string
	ModelExtra    map[string]any
	ThinkingMode  string
	SkillsDir     string
	WorkspaceDir  string
	MaxSteps      int
	ContextWindow int
	MaxToken      int
}

// Agent 持有无状态、可并发复用的 Eino DeepAgent 定义；
// 会话身份、历史消息与用量指标均在每次 Run() 时按请求隔离注入。
type Agent struct {
	agent adk.Agent
	log   *zap.Logger
}

// AgentDeps 由 cmd/server 统一注入。
// 常规生产装配只需提供 Model + Conversations + Attachments + Search + ShellTimeout；
// Tools / Shell 字段留作测试覆写扩展点（非空时跳过默认构建）。
type AgentDeps struct {
	Model         model.ToolCallingChatModel
	Conversations *conversations.Store
	Attachments   *attachments.Store
	Search        SearchConfig
	ShellTimeout  time.Duration
	Tools         []tool.BaseTool // 可选：非空时直接作为外部业务工具列表（便于单元测试注入）。
	Shell         adkfs.Shell     // 可选：非空时替换默认会话工作区 Shell。
	Config        Config
	Log           *zap.Logger
}

// Enabled 表示模型与代理已就绪；未配置 APIKey 时为 false，业务非对话接口仍可正常服务。
func (a *Agent) Enabled() bool { return a != nil && a.agent != nil }

// New 装配完整的主代理、子代理、中间件与工具链；不执行对话，也不持有任何会话态。
func New(ctx context.Context, d AgentDeps) (*Agent, error) {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	if d.Model == nil {
		return &Agent{log: log}, nil
	}

	cfg, err := normalizeConfig(d.Config)
	if err != nil {
		return nil, err
	}
	// 将 Eino 内置工具描述切换为中文，主角色提示词仍由 prompt.md 提供。
	_ = adk.SetLanguage(adk.LanguageChinese)

	// 1. 构建外部业务工具与会话 Shell（生产路径在包内闭环，彻底消除跨包回调倒手）。
	externalTools := d.Tools
	if externalTools == nil && d.Attachments != nil && d.Conversations != nil {
		var searchEnabled bool
		externalTools, searchEnabled, err = buildBuiltinTools(d.Attachments, d.Conversations, d.Search)
		if err != nil {
			return nil, err
		}
		if searchEnabled {
			log.Info("联网搜索能力已启用", zap.String("provider", d.Search.Provider))
		}
	}
	sh := d.Shell
	if sh == nil {
		sh = newShell(d.ShellTimeout, cfg.SkillsDir)
	}

	// 2. 初始化零信任虚拟文件系统、只读技能中间件与共享安全守卫。
	backend, err := newWorkspace(cfg.WorkspaceDir, cfg.SkillsDir)
	if err != nil {
		return nil, fmt.Errorf("初始化文件系统 Backend 失败: %w", err)
	}
	guard := newToolGuard(cfg.SkillsDir, defaultTaskTimeout)
	fsMW, err := newFilesystemMiddleware(ctx, backend, sh, false)
	if err != nil {
		return nil, err
	}
	skillBackend, err := skill.NewBackendFromFilesystem(ctx, &skill.BackendFromFilesystemConfig{
		Backend: backend, BaseDir: MountSkills,
	})
	if err != nil {
		return nil, fmt.Errorf("初始化技能后端失败: %w", err)
	}
	skillMW, err := skill.NewMiddleware(ctx, &skill.Config{Backend: skillBackend})
	if err != nil {
		return nil, fmt.Errorf("初始化技能 Middleware 失败: %w", err)
	}

	// 3. 装配上下文治理中间件：断链修复 -> 50% 水位清理 -> Todo 提醒 -> 预算计量 -> 80% 自动摘要 -> 思考路由。
	patchMW, err := patchtoolcalls.New(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("初始化 PatchToolCalls Middleware 失败: %w", err)
	}
	budget := newTokenBudget(cfg.ContextWindow, cfg.MaxToken, AgentName)
	reduceMW, err := newReductionMiddleware(ctx, budget)
	if err != nil {
		return nil, err
	}
	todoMW, err := newTodo()
	if err != nil {
		return nil, err
	}
	compaction, err := newContextCompaction(ctx, d.Model, budget)
	if err != nil {
		return nil, err
	}
	thinking := newThinking(cfg.ThinkingMode, cfg.ModelProvider, cfg.ModelExtra)

	// 4. 装配独立上下文的子代理（explorer 只读检索 / worker 小步执行）。
	subs, err := newSubAgents(ctx, d.Model, backend, sh, externalTools, cfg, guard)
	if err != nil {
		return nil, err
	}

	// 5. 装配 Eino DeepAgent：循环、工具分发与 task 委派均由框架实现。
	native, err := deep.New(ctx, &deep.Config{
		Name:        AgentName,
		Description: AgentDescription,
		ChatModel:   d.Model,
		Instruction: assemblePrompt(),
		SubAgents:   subs,
		ToolsConfig: adk.ToolsConfig{
			ToolsNodeConfig: compose.ToolsNodeConfig{
				Tools:               externalTools,
				UnknownToolsHandler: unknownToolHandler,
			},
		},
		MaxIteration:                 cfg.MaxSteps,
		WithoutWriteTodos:            true, // 使用项目自带 3 步防遗忘提醒与状态校验的 write_todos。
		WithoutGeneralSubAgent:       true, // 仅开放受控的 explorer 与 worker，不暴露无边界通用子代理。
		TaskToolDescriptionGenerator: taskToolDescription,
		Handlers: []adk.ChatModelAgentMiddleware{
			guard, fsMW, skillMW, patchMW, reduceMW, todoMW, budget, compaction, thinking,
		},
		ModelRetryConfig: &adk.ModelRetryConfig{
			MaxRetries:  1,
			ShouldRetry: retryOnEmptyOutput,
		},
	})
	if err != nil {
		return nil, fmt.Errorf("构建 TutorAgent 失败: %w", err)
	}

	var toolNames []string
	for _, t := range externalTools {
		if info, err := t.Info(ctx); err == nil && info != nil {
			toolNames = append(toolNames, info.Name)
		}
	}
	log.Info("TutorAgent 已装配",
		zap.Int("max_iteration", cfg.MaxSteps),
		zap.Strings("external_tools", toolNames),
	)
	return &Agent{agent: native, log: log}, nil
}

func normalizeConfig(cfg Config) (Config, error) {
	cfg.WorkspaceDir = cmp.Or(strings.TrimSpace(cfg.WorkspaceDir), DefaultWorkspaceDir)
	cfg.SkillsDir = cmp.Or(strings.TrimSpace(cfg.SkillsDir), DefaultSkillsDir)
	if cfg.MaxSteps <= 0 {
		cfg.MaxSteps = 40
	}
	if cfg.ContextWindow == 0 {
		cfg.ContextWindow = 1000000
	}
	if cfg.MaxToken == 0 {
		cfg.MaxToken = 131072
	}
	if cfg.ContextWindow <= 0 || cfg.MaxToken <= 0 {
		return cfg, fmt.Errorf("context_window 和 max_token 必须为正数")
	}
	return cfg, nil
}

// newFilesystemMiddleware 基于 Eino 官方 filesystem.New 装配文件工具与可选 Shell；
// readOnly=true 时同时禁用 write/edit/execute，供 explorer 子代理复用。
func newFilesystemMiddleware(ctx context.Context, backend adkfs.Backend, shell adkfs.Shell, readOnly bool) (adk.ChatModelAgentMiddleware, error) {
	if readOnly {
		shell = nil
	}
	mw, err := fsMiddleware.New(ctx, &fsMiddleware.MiddlewareConfig{
		Backend:             backend,
		Shell:               shell,
		ReadFileToolConfig:  &fsMiddleware.ToolConfig{Desc: &readFileDesc},
		WriteFileToolConfig: &fsMiddleware.ToolConfig{Desc: &writeFileDesc, Disable: readOnly},
		EditFileToolConfig:  &fsMiddleware.ToolConfig{Desc: &editFileDesc, Disable: readOnly},
		GrepToolConfig:      &fsMiddleware.ToolConfig{Desc: &grepDesc},
	})
	if err != nil {
		return nil, fmt.Errorf("初始化文件系统 Middleware 失败: %w", err)
	}
	return mw, nil
}

// newReductionMiddleware 基于窗口 50% 水位线启用 Eino 原生旧工具结果清理：
//   - 常规轮次低于 50% 不触发，保留完整多步工作记忆与供应商 Prompt Cache 前缀命中；
//   - ClearAtLeastTokens >= 1 同时触发 Eino 的深拷贝路径（copyMessagesGeneric），
//     确保不会原地修改已进入 Transcript 的历史消息指针。
func newReductionMiddleware(ctx context.Context, budget *tokenBudget) (adk.ChatModelAgentMiddleware, error) {
	return reduction.New(ctx, &reduction.Config{
		SkipTruncation: true,
		TokenCounter: func(_ context.Context, msgs []*schema.Message, tools []*schema.ToolInfo) (int64, error) {
			return budget.count(msgs, tools)
		},
		MaxTokensForClear:         max(1, int64(budget.window/2)),
		ClearAtLeastTokens:        max(1, int64(budget.window/20)),
		ClearRetentionSuffixLimit: 1,
		ClearExcludeTools:         []string{"skill", "write_todos"},
	})
}

// unknownToolHandler 将模型编造的未注册工具名转为温和反馈，避免整轮直接报错中止。
func unknownToolHandler(_ context.Context, name, _ string) (string, error) {
	return fmt.Sprintf("工具 %q 不存在。请只调用已提供的内置工具或外部工具，不要编造工具名。", name), nil
}

// assemblePrompt 合并静态角色规范（prompt.md）与宿主机环境信息；日期与附件留给每轮 <turn_context>。
func assemblePrompt() string {
	osArch := runtime.GOOS + "/" + runtime.GOARCH
	shellName, _ := hostShell()
	wsEnv, skillsEnv, findHint := "$WORKSPACE", "$SKILLS_DIR", "command -v node`、`which python3`、`npm root -g"
	if shellName == "cmd" {
		wsEnv, skillsEnv, findHint = "%WORKSPACE%", "%SKILLS_DIR%", "where node`、`where python`、`npm root -g"
	}

	var sb strings.Builder
	sb.WriteString("<environment>\n")
	fmt.Fprintf(&sb, "- 宿主机系统：`%s`，命令执行器：`%s`（严格使用当前系统 Shell 语法）。\n", osArch, shellName)
	sb.WriteString("- 文件工具虚拟路径：`/workspace`（可读写，存放全部产物），`/skills`（严格只读）；禁止写宿主机绝对路径。\n")
	fmt.Fprintf(&sb, "- `execute` 默认在工作区目录执行，直接用相对路径；需绝对路径时用 `%s` / `%s`；定位运行时用 `%s`。\n", wsEnv, skillsEnv, findHint)
	sb.WriteString("- 每轮日期、工作区文件列表与附件路径由用户消息 `<turn_context>` 提供。\n")
	sb.WriteString("- 附件仅支持 DOC、DOCX、PDF、Markdown，不支持图片输入。\n")
	sb.WriteString("</environment>")
	return strings.TrimSpace(basePrompt) + "\n\n" + sb.String()
}

// retryOnEmptyOutput 严格仅在「无报错且模型返回空响应」时重试 1 次；
// 任何模型/网络/超时报错一律不自动重试，交由上层日志记录并提示用户。
func retryOnEmptyOutput(ctx context.Context, rc *adk.TypedRetryContext[*schema.Message]) *adk.TypedRetryDecision[*schema.Message] {
	d := &adk.TypedRetryDecision[*schema.Message]{}
	if rc == nil {
		return d
	}
	if err := ctx.Err(); err != nil {
		d.RewriteError = err
		return d
	}
	if rc.Err != nil {
		return d
	}

	msg := rc.OutputMessage
	if msg != nil && (strings.TrimSpace(msg.Content) != "" || len(msg.ToolCalls) > 0 || len(msg.AssistantGenMultiContent) > 0) {
		return d
	}

	logutil.FromContext(ctx, nil).Warn("[模型空响应]", usageLogFields(msg, 0)...)
	// RetryAttempt 从 1 开始；剩余时间不足 2 秒时直接结束，避免启动无机会完成的重试。
	if rc.RetryAttempt <= 1 {
		if dl, ok := ctx.Deadline(); !ok || time.Until(dl) >= minRetryRemaining {
			d.Retry = true
			d.RejectReason = errEmptyAgentOutput.Error()
			return d
		}
	}
	d.RewriteError = errEmptyAgentOutput
	return d
}
