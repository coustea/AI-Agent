package chat

import (
	"context"
	"errors"
	"fmt"
	"io"
	"strings"

	"github.com/cloudwego/eino/adk"
	adkfs "github.com/cloudwego/eino/adk/filesystem"
	"github.com/cloudwego/eino/adk/middlewares/filesystem"
	"github.com/cloudwego/eino/adk/middlewares/reduction"
	"github.com/cloudwego/eino/adk/middlewares/skill"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
)

// ErrEmptyAnswer 表示模型没有产出任何可用回答。
var ErrEmptyAnswer = errors.New("模型未返回有效回答")

// Chunk 是流式输出的一个片段。
// Text 非空表示增量文本；Reset 为 true 表示要求客户端清空已渲染内容
// （发生在模型调用工具前的过渡语之后——那段话不属于最终回答）。
type Chunk struct {
	Text  string
	Reset bool
}

// StreamResult 是一轮流式执行的最终结果。
type StreamResult struct {
	// Answer 最终回答（最后一次 reset 之后累积的全部文本）
	Answer string
	// Usage 模型返回的真实 token 用量，nil 表示供应商未返回
	Usage *schema.TokenUsage
	// ToolCalls 本轮调用过的工具名，便于观察与测试断言
	ToolCalls []string
	// Resets 触发 reset 的次数
	Resets int
	// HasToolOutput 本轮是否产生过工具结果消息（区别于「发起工具调用」）
	HasToolOutput bool
}

// accumulator 维护「当前回答缓冲区」。
//
// reset 语义：模型在调用工具前常先输出一句过渡语（如「让我看一下文件」），
// 然后发起工具调用，等工具返回后再输出真正的回答。过渡语不属于最终回答，
// 因此一旦检测到工具调用就要清空缓冲并通知客户端丢弃已渲染内容。
type accumulator struct {
	buf   strings.Builder
	sink  func(Chunk) error
	stats *StreamResult
}

// appendText 追加文本并推给客户端。
func (a *accumulator) appendText(text string) error {
	if text == "" {
		return nil
	}
	a.buf.WriteString(text)
	return emit(a.sink, Chunk{Text: text})
}

// reset 清空缓冲并通知客户端。
func (a *accumulator) reset() error {
	if a.buf.Len() == 0 {
		return nil
	}
	a.buf.Reset()
	a.stats.Resets++
	return emit(a.sink, Chunk{Reset: true})
}

// answer 返回当前累积的回答。
func (a *accumulator) answer() string {
	return strings.TrimSpace(a.buf.String())
}

// Stream 遍历 runner 的事件流，把增量文本推给 sink，并返回最终回答。
//
// 处理规则：
//   - 工具结果事件只记录工具名，内容不进回答；
//   - assistant 流式事件逐块读取、累积并推送；
//   - 一旦某个块携带 ToolCalls，立即 reset（丢弃此前的过渡语）；
//   - 捕获末包 ResponseMeta.Usage 作为真实用量；
//   - ctx 取消时立刻返回，由上层落库 cancelled。
func Stream(ctx context.Context, runner *adk.Runner, messages []*schema.Message, sink func(Chunk) error) (*StreamResult, error) {
	if runner == nil {
		return nil, fmt.Errorf("runner 为空")
	}

	iter := runner.Run(ctx, messages)

	res := &StreamResult{}
	acc := &accumulator{sink: sink, stats: res}

	for {
		// 先检查取消：客户端断开后不应继续消费事件。
		if err := ctx.Err(); err != nil {
			res.Answer = acc.answer()
			return res, err
		}

		event, ok := iter.Next()
		if !ok {
			break
		}
		if event.Err != nil {
			res.Answer = acc.answer()
			return res, event.Err
		}
		if event.Output == nil || event.Output.MessageOutput == nil {
			continue
		}

		mv := event.Output.MessageOutput

		// 工具结果事件：只记录名字。
		if mv.Role == schema.Tool {
			res.HasToolOutput = true
			if mv.ToolName != "" {
				res.ToolCalls = append(res.ToolCalls, mv.ToolName)
			}
			continue
		}

		// 只关心 assistant 输出。
		if mv.Role != "" && mv.Role != schema.Assistant {
			continue
		}

		if mv.IsStreaming && mv.MessageStream != nil {
			if err := consumeStream(ctx, mv.MessageStream, acc); err != nil {
				res.Answer = acc.answer()
				return res, err
			}
			continue
		}

		if mv.Message == nil {
			continue
		}

		msg := mv.Message

		// 非流式消息里携带工具调用：先 reset 掉过渡语。
		if len(msg.ToolCalls) > 0 {
			for _, tc := range msg.ToolCalls {
				if tc.Function.Name != "" {
					res.ToolCalls = append(res.ToolCalls, tc.Function.Name)
				}
			}
			if err := acc.reset(); err != nil {
				res.Answer = acc.answer()
				return res, err
			}
			continue
		}

		if msg.ResponseMeta != nil && msg.ResponseMeta.Usage != nil {
			res.Usage = msg.ResponseMeta.Usage
		}

		if err := acc.appendText(msg.Content); err != nil {
			res.Answer = acc.answer()
			return res, err
		}
	}

	res.Answer = acc.answer()
	if res.Answer == "" {
		// 调用了工具但最终没有文本输出：这不算「模型没回答」。
		// 典型场景是模型完成文件写入/读取后不再追加说明，
		// 或达到 MaxIterations 前最后一轮只有工具调用。
		// 这类情况应视为成功，只是回答为空，由上层决定如何呈现。
		if len(res.ToolCalls) > 0 || res.HasToolOutput {
			return res, nil
		}
		return res, ErrEmptyAnswer
	}

	return res, nil
}

// consumeStream 消费一个流式消息，逐块累积并推送。
func consumeStream(ctx context.Context, sr *schema.StreamReader[*schema.Message], acc *accumulator) error {
	// 必须关闭，否则底层 goroutine 泄漏。
	defer sr.Close()

	for {
		chunk, err := sr.Recv()
		if err != nil {
			if errors.Is(err, io.EOF) {
				return nil
			}
			// ctx 取消时 Recv 会返回错误，交给上层按取消处理。
			if ctxErr := ctx.Err(); ctxErr != nil {
				return ctxErr
			}
			return err
		}
		if chunk == nil {
			continue
		}

		// 末包带真实用量。
		if chunk.ResponseMeta != nil && chunk.ResponseMeta.Usage != nil {
			acc.stats.Usage = chunk.ResponseMeta.Usage
		}

		// 工具调用：记录名字并立即 reset（丢弃此前的过渡语）。
		if len(chunk.ToolCalls) > 0 {
			for _, tc := range chunk.ToolCalls {
				if tc.Function.Name != "" {
					acc.stats.ToolCalls = append(acc.stats.ToolCalls, tc.Function.Name)
				}
			}
			if err := acc.reset(); err != nil {
				return err
			}
			continue
		}

		if err := acc.appendText(chunk.Content); err != nil {
			return err
		}
	}
}

// emit 安全地调用 sink。
func emit(sink func(Chunk) error, c Chunk) error {
	if sink == nil {
		return nil
	}
	return sink(c)
}

// ToSchemaMessages 把领域消息转换成 eino schema 消息。
//
// 放在本文件是因为这是「喂给模型」的最后一步：
// entity.go 刻意不依赖 eino，而 eino 的 schema 不该泄漏到业务代码里。
func ToSchemaMessages(msgs []Message) []*schema.Message {
	out := make([]*schema.Message, 0, len(msgs)+1)
	for _, m := range msgs {
		if strings.TrimSpace(m.Content) == "" {
			continue
		}
		role := schema.User
		if m.Role == RoleAssistant {
			role = schema.Assistant
		}
		out = append(out, &schema.Message{Role: role, Content: m.Content})
	}
	return out
}

// runnerSpec 是单轮 Agent 的装配参数。
// 所有字段都由 service 在 Pre-Run 之后确定，本文件不读配置、不查库。
type runnerSpec struct {
	// Instruction 已组装好的完整动态 System Prompt
	Instruction string
	// Workspace 会话工作目录（宿主机路径）
	Workspace string
	// OffloadDir 工具结果卸载目录（宿主机路径）
	OffloadDir string
	// MaxSteps Agent 单轮最大迭代步数
	MaxSteps int
}

// AgentRunner 封装 eino ADK：按轮构建无状态 Agent，并做「文本进文本出」的补全。
//
// 这是本包唯一认识 eino 的类型。Chunk / StreamResult 是它对外的形状，
// service 只依赖这两个类型，不直接碰 adk。
type AgentRunner struct {
	cm        model.ToolCallingChatModel
	skillsDir string
}

// NewAgentRunner 构造 runner。
// cm 为 nil 表示未配置模型，此时 chat 接口返回 503。
func NewAgentRunner(cm model.ToolCallingChatModel, skillsDir string) *AgentRunner {
	if cm == nil {
		return nil
	}
	return &AgentRunner{cm: cm, skillsDir: skillsDir}
}

// build 为本轮创建一个全新的 Agent 与 Runner。
// 每次调用都产出新实例，不共享任何可变状态。
func (r *AgentRunner) build(ctx context.Context, spec runnerSpec) (*adk.Runner, error) {
	if r.cm == nil {
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
	sandbox, err := NewSandbox(spec.Workspace, spec.OffloadDir, r.skillsDir)
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
	if strings.TrimSpace(r.skillsDir) != "" {
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

	ag, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
		Name:        "mentorly_tutor",
		Description: "Mentorly 学习辅导员，讲解计算机与工程学科知识",
		Instruction: spec.Instruction,
		Model:       r.cm,
		ToolsConfig: adk.ToolsConfig{
			ToolsNodeConfig: compose.ToolsNodeConfig{},
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

// Complete 走一次非流式生成，供会话标题与上下文摘要使用。
//
// 摘要与标题都属于「忠实改写」任务，同时需要稳定的结构化输出，
// 所以统一用低温；这里不暴露 temperature 参数，避免调用方各自为政。
func (r *AgentRunner) Complete(ctx context.Context, system, user string) (string, error) {
	if r == nil || r.cm == nil {
		return "", fmt.Errorf("LLM 未配置")
	}

	var temp float32 = 0.2
	msgs := []*schema.Message{
		schema.SystemMessage(system),
		schema.UserMessage(user),
	}

	resp, err := r.cm.Generate(ctx, msgs, model.WithTemperature(temp))
	if err != nil {
		return "", fmt.Errorf("LLM 生成失败: %w", err)
	}
	if resp == nil {
		return "", fmt.Errorf("LLM 返回空响应")
	}

	return resp.Content, nil
}

// 编译期断言：Sandbox 同时满足 reduction 的卸载后端要求（只需 Write），
// 若 eino 调整接口，这里会立刻编译失败而不是运行时才发现。
var _ adkfs.Backend = (*Sandbox)(nil)
