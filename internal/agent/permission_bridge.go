package agent

import (
	"context"
	"errors"
	"fmt"
	"sync/atomic"

	"my-agent/internal/protocol"
	"my-agent/pkg/llm"
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

// RespondPermission 异步审批权限请求（无状态，由 RequestID 关联）
func (a *CoreAgent) RespondPermission(requestID string, decision protocol.Decision) error {
	a.pendingMu.Lock()
	ch, ok := a.pendingPerms[requestID]
	a.pendingMu.Unlock()
	if !ok {
		return fmt.Errorf("agent: permission request %q not found or already resolved", requestID)
	}
	select {
	case ch <- decision:
		return nil
	default:
		return fmt.Errorf("agent: permission request %q is busy or channel closed", requestID)
	}
}

// permissionPreHook 作为 PreToolUse 钩子挂载在 tool.Registry 流水线上。
// 在工具实际调用前拦截高危行为与越界路径，直接阻断并返回错误作为 Observation 回灌。
func (a *CoreAgent) permissionPreHook(ctx context.Context, call llm.ToolCall) error {
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
