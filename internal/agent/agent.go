// Package agent 实现基于 Eino DeepAgent 的单 TutorAgent。
//
// 核心文件职责：
//   - agent.go       模型构造、系统提示词、DeepAgent 装配与模型重试策略
//   - middlewares/   全部 Eino ChatModelAgentMiddleware 装配与自定义 ToolGuard
//   - harness.go     单轮上下文准备（压缩检查点 + 完整历史 + 附件引用 + <turn_context>）
//   - chat.go        单轮流式执行、SSE 事件转换、状态/错误分类与 Token 统计日志
//   - workspace.go   虚拟文件系统 Backend（/workspace、/skills 隔离）
//   - tools/         外部业务工具（execute、list_attachments、read_attachment、web_search）
package agent

import (
	"context"
	_ "embed"
	"errors"
	"fmt"
	"maps"
	"net/url"
	"strings"
	"time"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/prebuilt/deep"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"

	"mentorly/internal/agent/middlewares"
	"mentorly/internal/agent/tools"
	logutil "mentorly/internal/utils/log"
)

// TutorAgent 对外暴露的名称、职责描述与默认目录约定。
const (
	AgentName           = "tutor"
	AgentDescription    = "通用学习智能体：讲解知识、分析附件、联网检索，并能自主创作文档、图解、课件与讲解视频"
	DefaultWorkspaceDir = "workspace/chat"
	DefaultSkillsDir    = "internal/agent/skills"
)

// ErrUnavailable 在模型未配置导致对话能力关闭时返回。
var ErrUnavailable = errors.New("对话能力未启用")

//go:embed prompt.md
var basePrompt string

// ---------- 模型构造 ----------

// ModelConfig 是构建 ChatModel 所需的最小参数集。
type ModelConfig struct {
	Provider string
	Model    string
	BaseURL  string
	APIKey   string
	MaxToken int
	Timeout  int64 // 秒
	Extra    map[string]any
}

// NewModel 按配置构建 Eino ChatModel；未配置 api_key 时返回 (nil, nil)。
func NewModel(ctx context.Context, cfg ModelConfig) (model.ToolCallingChatModel, error) {
	if strings.TrimSpace(cfg.APIKey) == "" {
		return nil, nil
	}
	switch strings.ToLower(strings.TrimSpace(cfg.Provider)) {
	case "spark":
		if strings.TrimSpace(cfg.BaseURL) == "" {
			cfg.BaseURL = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
		}
		if strings.TrimSpace(cfg.Model) == "" {
			cfg.Model = "spark-x2.6"
		}
	case "openai", "":
	default:
		return nil, fmt.Errorf("不支持的 llm.provider: %s", cfg.Provider)
	}

	baseURL, err := normalizeBaseURL(cfg.BaseURL)
	if err != nil {
		return nil, err
	}
	conf := &openai.ChatModelConfig{
		BaseURL: baseURL,
		APIKey:  strings.TrimSpace(cfg.APIKey),
		Model:   strings.TrimSpace(cfg.Model),
	}
	if cfg.MaxToken > 0 {
		conf.MaxTokens = &cfg.MaxToken
	}
	if cfg.Timeout > 0 {
		conf.Timeout = time.Duration(cfg.Timeout) * time.Second
	}
	if len(cfg.Extra) > 0 {
		conf.ExtraFields = cfg.Extra
	}
	cm, err := openai.NewChatModel(ctx, conf)
	if err != nil {
		return nil, fmt.Errorf("初始化 eino ChatModel 失败: %w", err)
	}
	return cm, nil
}

// normalizeBaseURL 校验并规范化模型地址，拒绝已含 /chat/completions 后缀以免 eino 重复拼接。
func normalizeBaseURL(raw string) (string, error) {
	base := strings.TrimRight(strings.TrimSpace(raw), "/")
	if base == "" {
		return "", fmt.Errorf("llm.base_url 不能为空")
	}
	u, err := url.Parse(base)
	if err != nil {
		return "", fmt.Errorf("llm.base_url 无法解析: %w", err)
	}
	if u.Hostname() == "" || (u.Scheme != "http" && u.Scheme != "https") {
		return "", fmt.Errorf("llm.base_url 必须是 http(s) 绝对地址，当前 %q", raw)
	}
	if strings.HasSuffix(strings.ToLower(u.Path), "/chat/completions") {
		return "", fmt.Errorf("llm.base_url 不能包含 /chat/completions（eino 会自行拼接），请改为 %q", strings.TrimSuffix(base, "/chat/completions"))
	}
	return base, nil
}

// ---------- Agent 装配 ----------

// Config 是 TutorAgent 的装配参数。
type Config struct {
	ModelProvider          string
	ModelExtra             map[string]any
	SkillsDir              string
	WorkspaceDir           string
	MaxSteps               int
	HistoryToolTurns       int
	ReduceTriggerTokens    int
	SummaryTriggerTokens   int
	SummaryTriggerMessages int
}

// Agent 是启动期构建一次并在多会话间复用的 TutorAgent。
type Agent struct {
	agent adk.Agent
	log   *zap.Logger
}

// AgentDeps 是 Agent 的装配参数；按分层约束不接受数据库仓储依赖。
type AgentDeps struct {
	Model  model.ToolCallingChatModel
	Tools  []tool.BaseTool
	Config Config
	Log    *zap.Logger
}

// Enabled 报告 Agent 是否可用（模型已配置）。
func (a *Agent) Enabled() bool { return a != nil && a.agent != nil }

// New 线性装配基于 Eino DeepAgent 的 TutorAgent 与全部中间件。
func New(ctx context.Context, d AgentDeps) (*Agent, error) {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	if d.Model == nil {
		return &Agent{log: log}, nil
	}

	cfg := d.Config
	if strings.TrimSpace(cfg.WorkspaceDir) == "" {
		cfg.WorkspaceDir = DefaultWorkspaceDir
	}
	if strings.TrimSpace(cfg.SkillsDir) == "" {
		cfg.SkillsDir = DefaultSkillsDir
	}
	if cfg.MaxSteps <= 0 {
		cfg.MaxSteps = 40
	}
	if cfg.HistoryToolTurns <= 0 {
		cfg.HistoryToolTurns = 2
	}
	if cfg.SummaryTriggerTokens <= 0 {
		cfg.SummaryTriggerTokens = 48000
	}
	if cfg.SummaryTriggerMessages <= 0 {
		cfg.SummaryTriggerMessages = 30
	}
	if cfg.ReduceTriggerTokens <= 0 {
		cfg.ReduceTriggerTokens = min(24000, cfg.SummaryTriggerTokens/2)
	}
	_ = adk.SetLanguage(adk.LanguageChinese)

	// 1. 虚拟文件系统（/workspace、/skills）。命令执行工具由外部 tools.NewShell 独立提供。
	backend, err := newWorkspace(cfg.WorkspaceDir, cfg.SkillsDir)
	if err != nil {
		return nil, fmt.Errorf("初始化文件系统 Backend 失败: %w", err)
	}

	// 2. 按生效顺序装配全部 ChatModelAgentMiddleware（完整链路见 middlewares/build.go）。
	handlers, err := middlewares.Build(ctx, middlewares.Config{
		Model:                  d.Model,
		Backend:                backend,
		MountSkills:            MountSkills,
		MountWorkspace:         MountWorkspace,
		ReadAttachmentTool:     tools.ToolReadAttachment,
		HistoryToolTurns:       cfg.HistoryToolTurns,
		ReduceTriggerTokens:    cfg.ReduceTriggerTokens,
		SummaryTriggerTokens:   cfg.SummaryTriggerTokens,
		SummaryTriggerMessages: cfg.SummaryTriggerMessages,
		IsTransient:            isTransient,
		ToolGuard:              toolGuardConfig(cfg.SkillsDir),
	})
	if err != nil {
		return nil, err
	}

	// 3. 装配 DeepAgent（Instruction 在启动期固定以命中前缀缓存，每轮易变状态走 <turn_context>）。
	native, err := deep.New(ctx, &deep.Config{
		Name:        AgentName,
		Description: AgentDescription,
		ChatModel:   d.Model,
		Instruction: assemblePrompt(),
		ToolsConfig: adk.ToolsConfig{
			ToolsNodeConfig: compose.ToolsNodeConfig{
				Tools: d.Tools,
				// 未知工具名转为文本反馈，避免模型幻觉工具名直接中断整轮对话。
				UnknownToolsHandler: func(_ context.Context, name, _ string) (string, error) {
					return fmt.Sprintf("工具 %q 不存在。请只调用已提供的内置工具或外部工具，不要编造工具名。", name), nil
				},
			},
		},
		MaxIteration: cfg.MaxSteps,
		Backend:      backend,
		Handlers:     handlers,
		ModelRetryConfig: &adk.ModelRetryConfig{
			MaxRetries:  3,
			ShouldRetry: newRetryDecision(cfg.ModelProvider, cfg.ModelExtra),
		},
	})
	if err != nil {
		return nil, fmt.Errorf("构建 TutorAgent 失败: %w", err)
	}

	var toolNames []string
	for _, t := range d.Tools {
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

// toolGuardConfig 组装 ToolGuard 所需的隔离路径与错误分类回调。
func toolGuardConfig(skillsDir string) middlewares.ToolGuardConfig {
	if strings.TrimSpace(skillsDir) == "" {
		skillsDir = DefaultSkillsDir
	}
	return middlewares.ToolGuardConfig{
		SkillsRoot:     skillsDir,
		MountSkills:    MountSkills,
		MountWorkspace: MountWorkspace,
		WorkspaceOf: func(ctx context.Context) string {
			if run, ok := principalFrom(ctx); ok {
				return run.Workspace
			}
			return ""
		},
		FatalErrors: []error{errNoPrincipal},
		FormatError: formatWorkspaceError,
	}
}

// ---------- 系统提示词 ----------

// assemblePrompt 在启动期拼装静态 System Prompt；每轮变化的日期/文件/附件不写在此处，避免破坏缓存。
func assemblePrompt() string {
	osArch, shellName := tools.HostShellInfo()
	wsEnv, skillsEnv, findHint := "$WORKSPACE", "$SKILLS_DIR", "command -v node`、`which python3`、`npm root -g"
	if shellName == "cmd" {
		wsEnv, skillsEnv, findHint = "%WORKSPACE%", "%SKILLS_DIR%", "where node`、`where python`、`npm root -g"
	}

	var sb strings.Builder
	sb.WriteString("---\n\n## 当前运行环境\n\n")
	fmt.Fprintf(&sb, "- 宿主机系统：`%s`，命令执行器：`%s`（请严格使用当前操作系统与 Shell 支持的语法）。\n", osArch, shellName)
	sb.WriteString("- 文件系统挂载点：\n")
	sb.WriteString("  - `/workspace` 你的工作目录，可读写，所有产出都放这里\n")
	sb.WriteString("  - `/skills` 技能目录，**严格只读**，只能读不能写\n")
	sb.WriteString("- 文件工具路径必须使用这些虚拟路径的绝对形式，不要写宿主机路径。\n")
	sb.WriteString("- 每轮对话的日期、工作区文件列表与附件路径由当轮用户消息给出，以消息为准。\n")
	fmt.Fprintf(&sb, "- 你可以用 `execute` 执行 `%s` 命令：\n", shellName)
	sb.WriteString("  - **命令的当前目录就是工作区本身**，直接用相对路径（如 `python3 script.py`）\n")
	fmt.Fprintf(&sb, "  - 需要工作区或技能目录绝对路径时使用环境变量 `%s` / `%s`，不要写 `/workspace` 或 `/skills`——那是文件工具用的虚拟路径\n", wsEnv, skillsEnv)
	fmt.Fprintf(&sb, "  - 需要定位运行时或全局依赖路径时，直接用标准命令查找（如 `%s`）\n", findHint)
	sb.WriteString("  - 所有产出只写工作区，严禁修改技能目录，高危命令会被安全中间件拦截\n")
	sb.WriteString("  - 需要联网查询外部资料请优先使用 `web_search` 工具\n")
	sb.WriteString("  - 单条命令有超时限制，长任务请拆成多条并关注输出\n")
	sb.WriteString("- 附件仅支持 DOC、DOCX、PDF 和 Markdown 文档，不支持图片输入。\n")
	return strings.TrimSpace(basePrompt) + "\n\n" + sb.String()
}

// ---------- 模型重试策略 ----------

const (
	minRetryRemaining    = 2 * time.Second
	minFallbackRemaining = 20 * time.Second
)

// newRetryDecision 构建 Eino 原生模型重试决策（仅重调当前模型，不重跑已完成工具）：
// - 429/瞬时网络错误：确认剩余 deadline 足够后退避重试；
// - finish_reason=length 空响应：spark 推理耗尽时通过 AdditionalOptions 仅本次关闭思考降级重试 1 次，否则立即报截断错；
// - 非 length 的偶发空响应：允许原样重试 1 次。
func newRetryDecision(provider string, baseExtra map[string]any) func(context.Context, *adk.TypedRetryContext[*schema.Message]) *adk.TypedRetryDecision[*schema.Message] {
	isSpark := strings.EqualFold(strings.TrimSpace(provider), "spark")
	extraCopy := maps.Clone(baseExtra)

	return func(ctx context.Context, rc *adk.TypedRetryContext[*schema.Message]) *adk.TypedRetryDecision[*schema.Message] {
		d := &adk.TypedRetryDecision[*schema.Message]{}
		if rc == nil {
			return d
		}
		if err := ctx.Err(); err != nil {
			d.RewriteError = err
			return d
		}
		if rc.Err != nil {
			if !errors.Is(rc.Err, context.Canceled) && !errors.Is(rc.Err, context.DeadlineExceeded) && isTransient(rc.Err) {
				var backoff time.Duration
				if isRateLimit(rc.Err) {
					backoff = min(time.Duration(max(rc.RetryAttempt, 1))*3*time.Second, 10*time.Second)
				}
				if hasRemaining(ctx, backoff+minRetryRemaining) {
					d.Retry, d.Backoff = true, backoff
				}
			}
			return d
		}

		msg := rc.OutputMessage
		if msg != nil && (strings.TrimSpace(msg.Content) != "" || len(msg.ToolCalls) > 0 || len(msg.AssistantGenMultiContent) > 0) {
			return d
		}

		reason := finishReasonOf(msg)
		logger := logutil.FromContext(ctx, nil)
		logger.Warn("[模型空响应]", usageLogFields(msg, 0)...)

		if reason == "length" {
			if rc.RetryAttempt == 1 && isSpark && hasReasoning(msg) && hasRemaining(ctx, minFallbackRemaining) {
				logger.Warn("[模型降级重试]", zap.String("策略", "thinking=disabled"), zap.String("结束原因", reason))
				merged := make(map[string]any, len(extraCopy)+1)
				maps.Copy(merged, extraCopy)
				// WithExtraFields 会整体替换 map，必须先拷贝基础 extra_fields 再写入 thinking。
				merged["thinking"] = map[string]any{"type": "disabled"}
				d.Retry = true
				d.AdditionalOptions = []model.Option{openai.WithExtraFields(merged)}
				d.RejectReason = errOutputTruncated.Error()
				return d
			}
			logger.Warn("[模型输出截断]", zap.String("结束原因", reason))
			d.RewriteError = errOutputTruncated
			return d
		}

		if rc.RetryAttempt <= 1 && hasRemaining(ctx, minRetryRemaining) {
			d.Retry = true
			d.RejectReason = errEmptyAgentOutput.Error()
		} else {
			logger.Warn("[模型重试失败]", logutil.Content("错误", errEmptyAgentOutput.Error()))
			d.RewriteError = errEmptyAgentOutput
		}
		return d
	}
}

// hasRemaining 检查 context 距离 deadline 是否至少还剩 need 时长，避免临近超时仍发起重试。
func hasRemaining(ctx context.Context, need time.Duration) bool {
	dl, ok := ctx.Deadline()
	return !ok || time.Until(dl) >= need
}

// hasReasoning 判断本次模型响应是否消耗了推理过程（文本或 reasoning_tokens）。
func hasReasoning(msg *schema.Message) bool {
	if msg == nil {
		return false
	}
	if strings.TrimSpace(msg.ReasoningContent) != "" {
		return true
	}
	return msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil && msg.ResponseMeta.Usage.CompletionTokensDetails.ReasoningTokens > 0
}

// isRateLimit 判断错误是否为上游限流（429），用于触发指数退避。
func isRateLimit(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "429") || strings.Contains(msg, "rate limit") ||
		strings.Contains(msg, "frequency limit") || strings.Contains(msg, "too many requests")
}
