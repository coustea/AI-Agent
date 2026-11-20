package tutor

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/cloudwego/eino/adk"
	adkfs "github.com/cloudwego/eino/adk/filesystem"
	"github.com/cloudwego/eino/adk/middlewares/filesystem"
	"github.com/cloudwego/eino/adk/middlewares/reduction"
	"github.com/cloudwego/eino/adk/middlewares/skill"
	"github.com/cloudwego/eino/adk/middlewares/summarization"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
	"go.uber.org/zap"

	"mentorly/internal/agents/tutor/middleware"
)

// AgentName 是 TutorAgent 在 Eino 中的名称。
const AgentName = "tutor"

// AgentDescription 用于未来作为 AgentTool 被其他 Agent 调用时识别。
const AgentDescription = "Mentorly 教学智能体，讲解计算机与工程学科知识，可生成图解、课件与讲解视频"

// Config 是 TutorAgent 的构建参数。
//
// 全部字段由 app 层从全局配置拍平后传入：
// 本包不 import internal/config，对配置文件形状零知识。
type Config struct {
	// SkillsDir 技能目录宿主机路径，只读挂载为 /skills
	SkillsDir string
	// MaxSteps 单轮最大 ReAct 迭代次数
	MaxSteps int
	// SummaryTriggerTokens 触发摘要压缩的 token 阈值
	SummaryTriggerTokens int
	// SummaryTriggerMessages 触发摘要压缩的消息条数阈值
	SummaryTriggerMessages int
	// Vision 模型是否支持图片原生输入
	Vision bool
}

// Agent 是 TutorAgent 的构建器。
//
// 每次运行都会调用 Build 创建一个全新的 Agent 与 Runner：
// Eino 的 Agent 在运行期间持有会话状态，跨请求复用会造成状态串扰。
type Agent struct {
	cm     model.ToolCallingChatModel
	tools  []tool.BaseTool
	cfg    Config
	log    *zap.Logger
	skills string
}

// New 构造构建器。
//
// cm 为 nil 表示未配置模型，此时 Enabled() 为 false，
// 上层应返回 503 而不是尝试运行。
func New(cm model.ToolCallingChatModel, tools []tool.BaseTool, cfg Config, log *zap.Logger) *Agent {
	if log == nil {
		log = zap.NewNop()
	}
	if cfg.MaxSteps <= 0 {
		cfg.MaxSteps = 12
	}
	return &Agent{
		cm:     cm,
		tools:  tools,
		cfg:    cfg,
		log:    log,
		skills: strings.TrimSpace(cfg.SkillsDir),
	}
}

// Enabled 判断 Agent 是否可用。
func (a *Agent) Enabled() bool {
	return a != nil && a.cm != nil
}

// BuildSpec 是一次构建所需的运行期参数。
type BuildSpec struct {
	// Instruction 已组装好的 System Prompt
	Instruction string
	// Sandbox 本次运行的文件系统边界
	Sandbox adkfs.Backend
}

// Build 创建本轮使用的 Runner。
//
// Middleware 全部使用 Eino 官方实现，顺序有讲究：
//
//  1. filesystem  提供 ls/read/write/edit/glob/grep，必须最先（其他中间件依赖 Backend）
//  2. skill       技能渐进式加载
//  3. summarization 上下文压缩（官方实现，替代自研 compress.go）
//  4. reduction   工具结果过大时卸载到 /.offload
//  5. toolGuard   工具权限与配额（唯一自定义中间件）
//
// 自定义中间件放在最后：它是最内层包装，能拦住前面所有中间件
// 最终放行到工具执行的那一次调用。
func (a *Agent) Build(ctx context.Context, spec BuildSpec) (*adk.Runner, error) {
	if !a.Enabled() {
		return nil, ErrUnavailable
	}
	if spec.Sandbox == nil {
		return nil, fmt.Errorf("沙箱后端不能为空")
	}

	handlers := make([]adk.ChatModelAgentMiddleware, 0, 5)

	// 1. filesystem：Agent 的读写能力基础
	fsMW, err := filesystem.New(ctx, &filesystem.MiddlewareConfig{
		Backend: spec.Sandbox,
	})
	if err != nil {
		return nil, fmt.Errorf("创建 filesystem 中间件失败: %w", err)
	}
	handlers = append(handlers, fsMW)

	// 2. skill：渐进式加载，只注入名称与简介
	if a.skills != "" {
		backend, err := skill.NewBackendFromFilesystem(ctx, &skill.BackendFromFilesystemConfig{
			Backend: spec.Sandbox,
			BaseDir: MountSkills,
		})
		if err != nil {
			return nil, fmt.Errorf("创建 skill backend 失败: %w", err)
		}

		skillMW, err := skill.NewMiddleware(ctx, &skill.Config{Backend: backend})
		if err != nil {
			return nil, fmt.Errorf("创建 skill 中间件失败: %w", err)
		}
		handlers = append(handlers, skillMW)
	}

	// 3. summarization：官方上下文压缩
	//
	// 用官方实现替代原先自研的 compress.go（约 300 行 + 341 行窗口裁剪）。
	// 官方实现会在超过阈值时把旧消息压成摘要，原始消息仍完整保留在数据库，
	// 因此前端历史记录不受影响。
	sumMW, err := summarization.New(ctx, &summarization.Config{
		Model: a.cm,
		Trigger: &summarization.TriggerCondition{
			ContextTokens:   a.cfg.SummaryTriggerTokens,
			ContextMessages: a.cfg.SummaryTriggerMessages,
		},
	})
	if err != nil {
		return nil, fmt.Errorf("创建 summarization 中间件失败: %w", err)
	}
	handlers = append(handlers, sumMW)

	// 4. reduction：单轮内工具结果过大时卸载
	redMW, err := reduction.New(ctx, &reduction.Config{
		Backend:           spec.Sandbox,
		RootDir:           MountOffload,
		MaxTokensForClear: 20000,
	})
	if err != nil {
		return nil, fmt.Errorf("创建 reduction 中间件失败: %w", err)
	}
	handlers = append(handlers, redMW)

	// 5. toolGuard：权限与配额
	handlers = append(handlers, middleware.NewToolGuard(a.log))

	ag, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
		Name:        AgentName,
		Description: AgentDescription,
		Instruction: spec.Instruction,
		Model:       a.cm,
		ToolsConfig: adk.ToolsConfig{
			ToolsNodeConfig: compose.ToolsNodeConfig{
				Tools: a.tools,
			},
		},
		MaxIterations: a.cfg.MaxSteps,
		Handlers:      handlers,
		// 模型调用重试：上游网关偶发连接重置/EOF，重试即可恢复。
		// 上下文取消与超时重试无意义，必须排除。
		ModelRetryConfig: &adk.ModelRetryConfig{
			MaxRetries:  2,
			ShouldRetry: shouldRetry,
		},
	})
	if err != nil {
		return nil, fmt.Errorf("创建 ChatModelAgent 失败: %w", err)
	}

	return adk.NewRunner(ctx, adk.RunnerConfig{
		Agent:           ag,
		EnableStreaming: true,
	}), nil
}

// shouldRetry 只重试值得重试的瞬时错误。
func shouldRetry(_ context.Context, rc *adk.RetryContext) *adk.RetryDecision {
	if rc == nil || rc.Err == nil {
		return nil
	}
	if errors.Is(rc.Err, context.Canceled) || errors.Is(rc.Err, context.DeadlineExceeded) {
		return &adk.RetryDecision{Retry: false}
	}
	if isTransient(rc.Err) {
		return &adk.RetryDecision{Retry: true}
	}
	return &adk.RetryDecision{Retry: false}
}

// isTransient 判断是否为值得重试的瞬时错误。
//
// 典型来源：网关主动断开（EOF / connection reset）、429 限流、5xx。
// 参数错误与鉴权失败重试只会浪费时间。
func isTransient(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	for _, kw := range []string{
		"eof", "connection reset", "broken pipe", "timeout", "timed out",
		"429", "500", "502", "503", "504", "too many requests",
		"temporarily unavailable", "rate limit", "overloaded",
	} {
		if strings.Contains(msg, kw) {
			return true
		}
	}
	return false
}
