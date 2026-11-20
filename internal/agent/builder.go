package agent

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
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
)

// Spec 是单轮 Agent 的装配参数。
// 所有字段都由 Harness 在 Pre-Run 之后确定，Builder 本身不读配置、不查库。
type Spec struct {
	// Instruction 已组装好的完整动态 System Prompt
	Instruction string
	// Workspace 会话工作目录（宿主机路径）
	Workspace string
	// OffloadDir 工具结果卸载目录（宿主机路径）
	OffloadDir string
	// MaxSteps Agent 单轮最大迭代步数
	MaxSteps int
}

// Builder 按轮创建无状态 ChatModelAgent。
// 每次 Build 都产出全新实例与 Runner，不共享任何可变状态。
type Builder struct {
	cm        model.ToolCallingChatModel
	skillsDir string
	tools     []tool.BaseTool
}

// NewBuilder 构造 Builder。
// tools 为静态工具集（remember 等），文件工具由 filesystem 中间件动态注册。
func NewBuilder(cm model.ToolCallingChatModel, skillsDir string, tools ...tool.BaseTool) *Builder {
	return &Builder{cm: cm, skillsDir: skillsDir, tools: tools}
}

// Build 为本轮创建一个全新的 Agent 与 Runner。
func (b *Builder) Build(ctx context.Context, spec Spec) (*adk.Runner, error) {
	if b.cm == nil {
		return nil, fmt.Errorf("未配置 ChatModel，无法构建 Agent")
	}
	if strings.TrimSpace(spec.Workspace) == "" {
		return nil, fmt.Errorf("workspace 不能为空")
	}

	maxSteps := spec.MaxSteps
	if maxSteps <= 0 {
		maxSteps = 8
	}

	// 沙箱：把三个挂载点映射到宿主机目录，并负责全部越界校验。
	sandbox, err := NewSandbox(spec.Workspace, spec.OffloadDir, b.skillsDir)
	if err != nil {
		return nil, fmt.Errorf("创建沙箱失败: %w", err)
	}

	// filesystem 中间件注册 ls / read_file / write_file / edit_file / glob / grep。
	// 这些工具的参数 Schema 由 eino 提供，静态 Prompt 里不再重复说明。
	fsMW, err := filesystem.New(ctx, &filesystem.MiddlewareConfig{
		Backend: sandbox,
	})
	if err != nil {
		return nil, fmt.Errorf("创建 filesystem 中间件失败: %w", err)
	}

	handlers := []adk.ChatModelAgentMiddleware{fsMW}

	// skill 中间件：渐进式加载。仅注入技能名称与简介，
	// 模型需要细节时才读 /skills/{name}/SKILL.md，避免一次塞满上下文。
	if strings.TrimSpace(b.skillsDir) != "" {
		skillBackend, err := skill.NewBackendFromFilesystem(ctx, &skill.BackendFromFilesystemConfig{
			Backend: sandbox,
			BaseDir: MountSkills,
		})
		if err != nil {
			return nil, fmt.Errorf("创建 skill backend 失败: %w", err)
		}

		skMW, err := skill.NewMiddleware(ctx, &skill.Config{Backend: skillBackend})
		if err != nil {
			return nil, fmt.Errorf("创建 skill 中间件失败: %w", err)
		}
		handlers = append(handlers, skMW)
	}

	// reduction 中间件：单轮内工具结果过大时卸载到 /.offload，
	// 保证不会因为一次 grep 或 read 就把上下文打满。
	redMW, err := reduction.New(ctx, &reduction.Config{
		Backend:           sandbox,
		RootDir:           MountOffload,
		MaxTokensForClear: 20000,
	})
	if err != nil {
		return nil, fmt.Errorf("创建 reduction 中间件失败: %w", err)
	}
	handlers = append(handlers, redMW)

	// 过滤 nil 工具：NewRememberTool 在未启用记忆时返回 nil。
	tools := make([]tool.BaseTool, 0, len(b.tools))
	for _, t := range b.tools {
		if t != nil {
			tools = append(tools, t)
		}
	}

	ag, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
		Name:        "mentorly_tutor",
		Description: "Mentorly 学习辅导员，讲解计算机与工程学科知识",
		Instruction: spec.Instruction,
		Model:       b.cm,
		ToolsConfig: adk.ToolsConfig{
			ToolsNodeConfig: composeToolsNodeConfig(tools),
		},
		MaxIterations: maxSteps,
		Handlers:      handlers,
		// 模型调用重试：上游供应商（尤其国内网关）偶发连接被重置/EOF，
		// 这类瞬时故障重试即可恢复，不该让整轮对话失败。
		ModelRetryConfig: &adk.ModelRetryConfig{
			MaxRetries: 2,
			ShouldRetry: func(_ context.Context, rc *adk.RetryContext) *adk.RetryDecision {
				if rc.Err == nil {
					return nil
				}
				// 只重试瞬时网络/服务端错误；上下文取消与超时重试无意义。
				if errors.Is(rc.Err, context.Canceled) || errors.Is(rc.Err, context.DeadlineExceeded) {
					return &adk.RetryDecision{Retry: false}
				}
				if isTransientError(rc.Err) {
					return &adk.RetryDecision{Retry: true}
				}
				return &adk.RetryDecision{Retry: false}
			},
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

// isTransientError 判断是否为值得重试的瞬时错误。
//
// 典型来源：网关主动断开（EOF / connection reset）、429 限流、5xx。
// 这类错误重试通常能成功，而参数错误、鉴权失败重试只会浪费时间。
func isTransientError(err error) bool {
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

// composeToolsNodeConfig 把工具列表装配成 compose.ToolsNodeConfig。
// 单独抽出是为了让「工具为空」时也能得到合法配置（eino 接受空切片）。
func composeToolsNodeConfig(tools []tool.BaseTool) compose.ToolsNodeConfig {
	return compose.ToolsNodeConfig{Tools: tools}
}

// 编译期断言：Sandbox 同时满足 reduction 的卸载后端要求（只需 Write），
// 若 eino 调整接口，这里会立刻编译失败而不是运行时才发现。
var _ adkfs.Backend = (*Sandbox)(nil)
