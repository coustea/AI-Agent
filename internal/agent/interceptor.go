package agent

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
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
