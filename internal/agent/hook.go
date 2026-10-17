package agent

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"time"
	"unicode/utf8"

	"my-agent/internal/protocol"
)

type eventSinkKey struct{}

// withEventSink 在每轮对话开始时，将当前轮次的事件通道注入 context
func withEventSink(ctx context.Context, ch chan<- protocol.Event) context.Context {
	return context.WithValue(ctx, eventSinkKey{}, ch)
}

// eventSinkFrom 从 context 提取当前轮次的事件通道
func eventSinkFrom(ctx context.Context) (chan<- protocol.Event, bool) {
	ch, ok := ctx.Value(eventSinkKey{}).(chan<- protocol.Event)
	return ch, ok
}

// bridgeApproval 将权限审批请求桥接至本轮的事件流通道，等待用户交互审批
func (a *CoreAgent) bridgeApproval(ctx context.Context, req protocol.PermissionRequest) (protocol.Decision, error) {
	outCh, ok := eventSinkFrom(ctx)
	if !ok {
		return protocol.DecisionDeny, errors.New("no interactive approval channel available")
	}

	reqID := fmt.Sprintf("perm_%d", atomic.AddUint64(&a.permSeq, 1))
	req.RequestID = reqID
	respCh := make(chan protocol.Decision, 1)

	a.pendingMu.Lock()
	a.pendingPerms[reqID] = respCh
	a.pendingMu.Unlock()

	defer func() {
		a.pendingMu.Lock()
		delete(a.pendingPerms, reqID)
		a.pendingMu.Unlock()
	}()

	if !sendEvent(ctx, outCh, protocol.Event{
		Type:       protocol.EventPermissionReq,
		Permission: &req,
	}) {
		return protocol.DecisionDeny, ctx.Err()
	}

	select {
	case d := <-respCh:
		return d, nil
	case <-ctx.Done():
		return protocol.DecisionDeny, ctx.Err()
	}
}

// permissionPreHook 作为 PreToolUse 钩子挂载在 tool.Registry 流水线上。
// 在工具实际调用前拦截高危行为与越界路径，直接阻断并返回错误作为 Observation 回灌。
func (a *CoreAgent) permissionPreHook(ctx context.Context, call protocol.ToolCall) error {
	a.mu.RLock()
	perm := a.permission
	a.mu.RUnlock()

	if perm == nil {
		return nil
	}

	allowed, reason, err := perm.Evaluate(ctx, call)
	if err != nil {
		return fmt.Errorf("permission evaluation error: %w", err)
	}
	if !allowed {
		if reason == "" {
			reason = "permission denied"
		}
		return errors.New(reason)
	}
	return nil
}

const (
	toolResultBudgetRunes  = 8000 // 单条工具结果落盘阈值（字符数）
	toolResultPreviewRunes = 2000 // 落盘后保留的预览字符数
)

// largeResultPostHook 作为 PostToolUse 钩子挂载在 tool.Registry 流水线上。
// 学习自 learn-claude-code 的 PostToolUse 机制：
// 工具执行已完成，若输出内容过大（超过阈值），则全量落盘并改写为“前缀预览 + 完整路径提示”，
// 既防止单条工具大输出打爆模型上下文，又保留模型通过 read_file 回读全量内容的能力。
func (a *CoreAgent) largeResultPostHook(ctx context.Context, call protocol.ToolCall, res *protocol.ToolResult) {
	if res == nil || res.Content == "" {
		return
	}

	totalRunes := utf8.RuneCountInString(res.Content)
	if totalRunes <= toolResultBudgetRunes {
		return
	}

	a.mu.RLock()
	workDir := a.workDir
	a.mu.RUnlock()
	if workDir == "" {
		workDir = "."
	}

	resultsDir := filepath.Join(workDir, ".coustea", "tool-results")
	if err := os.MkdirAll(resultsDir, 0o755); err != nil {
		// 落盘目录创建失败则降级原样返回
		return
	}

	safeCallID := sanitizeFileName(call.ID)
	if safeCallID == "" {
		safeCallID = "result"
	}
	fileName := fmt.Sprintf("%s.txt", safeCallID)
	fullPath := filepath.Join(resultsDir, fileName)

	// 若存在同名冲突，追加数字后缀
	for i := 1; ; i++ {
		if _, err := os.Stat(fullPath); os.IsNotExist(err) {
			break
		}
		fileName = fmt.Sprintf("%s_%d.txt", safeCallID, i)
		fullPath = filepath.Join(resultsDir, fileName)
	}

	// 写入全量输出
	if err := os.WriteFile(fullPath, []byte(res.Content), 0o600); err != nil {
		// 写入失败降级保留原文本，不丢弃信息
		return
	}

	// 截取前预览字符
	runes := []rune(res.Content)
	preview := string(runes[:toolResultPreviewRunes])

	relPath, err := filepath.Rel(workDir, fullPath)
	if err != nil {
		relPath = fullPath
	}

	res.Content = fmt.Sprintf("%s\n\n... [output truncated: %d characters total; full content saved to %s — use read_file to view]", preview, totalRunes, filepath.ToSlash(relPath))
}

func sanitizeFileName(name string) string {
	clean := strings.TrimSpace(name)
	replacer := strings.NewReplacer("/", "_", "\\", "_", ":", "_", "*", "_", "?", "_", "\"", "_", "<", "_", ">", "_", "|", "_")
	return replacer.Replace(clean)
}

// ============================================================================
// Agent 生命周期切面钩子与追踪数据契约 (零侵入可观测性中间件)
// ============================================================================

// LLMRequestTrace 记录向大模型发送的完整请求快照
type LLMRequestTrace struct {
	Step         int                       // 当前 ReAct 迭代步数 (0-indexed)
	Provider     string                    // 当前模型提供商 (如 deepseek, gemini)
	ModelName    string                    // 当前模型规格名称 (如 deepseek-reasoner)
	SystemPrompt string                    // 本轮合成的完整 System Prompt
	Messages     []protocol.Message        // 包含历史与当前提问的完整上下文切片
	Tools        []protocol.ToolDefinition // 注入大模型的工具能力元定义
	Timestamp    time.Time                 // 请求发起时间
}

// LLMResponseTrace 记录大模型返回的完整决策快照
type LLMResponseTrace struct {
	Step             int                 // 当前 ReAct 迭代步数
	Duration         time.Duration       // 大模型流式耗时
	Reply            string              // 大模型返回的正文内容 (Markdown)
	ReasoningContent string              // 深度思考链内容 (DeepSeek Reasoner 等返回的 CoT)
	ToolCalls        []protocol.ToolCall // 大模型要求执行的工具调用列表
	Usage            *protocol.Usage     // 本次交互消耗的 Token (Prompt/Completion)
	Error            error               // 若发生网络或模型异常则记录
}

// ToolTrace 记录工具执行前后的完整快照
type ToolTrace struct {
	Step      int                 // 所属 ReAct 步骤
	Call      protocol.ToolCall   // 工具调用定义 (ID, Name, Arguments)
	Result    protocol.ToolResult // 工具执行返回值与错误标记
	Duration  time.Duration       // 工具调用耗时
	Timestamp time.Time           // 执行时间
}

// TurnSummaryTrace 记录一轮完整问答的汇总快照
type TurnSummaryTrace struct {
	TurnID     string         // 对话轮次唯一标识符 (如 turn_1713345678)
	Prompt     string         // 用户原始提问
	TotalSteps int            // 本轮共经历的 ReAct 循环迭代次数
	TotalUsage protocol.Usage // 本轮累计消耗的总 Token
	Duration   time.Duration  // 从提问到收敛的总耗时
	Success    bool           // 是否成功完成
	Error      error          // 异常信息 (若有)
}

// AgentHook 定义智能体生命周期横切切面。
// 遵循 Hook / Middleware 思想：任何日志、耗时统计、审计等横切逻辑均通过挂载此接口实现，核心循环零侵入。
type AgentHook interface {
	// OnTurnStart 单轮交互开始
	OnTurnStart(ctx context.Context, turnID string, prompt string)

	// OnLLMRequest 每步发起大模型调用前
	OnLLMRequest(ctx context.Context, req *LLMRequestTrace)

	// OnLLMResponse 大模型决策返回完毕后
	OnLLMResponse(ctx context.Context, resp *LLMResponseTrace)

	// OnToolStart 工具调用开始前
	OnToolStart(ctx context.Context, step int, call protocol.ToolCall)

	// OnToolEnd 工具调用执行完毕后
	OnToolEnd(ctx context.Context, trace *ToolTrace)

	// OnTurnEnd 单轮交互完整收敛结束
	OnTurnEnd(ctx context.Context, summary *TurnSummaryTrace)
}
