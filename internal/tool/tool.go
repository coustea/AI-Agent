package tool

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"

	"my-agent/internal/gateway"
)

// Tool 定义单个工具插件的标准接口
type Tool interface {
	Name() string
	Description() string
	Schema() json.RawMessage
	Execute(ctx context.Context, args json.RawMessage) (string, error)
}

// Registry 是线程安全的工具注册表
type Registry struct {
	mu    sync.RWMutex
	tools map[string]Tool
}

// NewRegistry 创建工具注册表并可选地预先注册一批工具
func NewRegistry(ts ...Tool) *Registry {
	r := &Registry{
		tools: make(map[string]Tool),
	}
	r.Register(ts...)
	return r
}

// Register 注册一个或多个工具
func (r *Registry) Register(ts ...Tool) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, t := range ts {
		if t != nil && t.Name() != "" {
			r.tools[t.Name()] = t
		}
	}
}

// Get 根据名称获取工具
func (r *Registry) Get(name string) (Tool, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	t, ok := r.tools[name]
	return t, ok
}

// Definitions 导出供大模型 Function Calling 使用的工具定义列表
func (r *Registry) Definitions() []gateway.ToolDefinition {
	r.mu.RLock()
	defer r.mu.RUnlock()

	defs := make([]gateway.ToolDefinition, 0, len(r.tools))
	for _, t := range r.tools {
		defs = append(defs, gateway.ToolDefinition{
			Name:        t.Name(),
			Description: t.Description(),
			Parameters:  t.Schema(),
		})
	}
	return defs
}

// Execute 校验参数并安全执行对应的工具
func (r *Registry) Execute(ctx context.Context, call gateway.ToolCall) (gateway.ToolResult, error) {
	r.mu.RLock()
	t, ok := r.tools[call.Name]
	r.mu.RUnlock()

	if !ok {
		return gateway.ToolResult{
			ToolCallID: call.ID,
			Name:       call.Name,
			Content:    fmt.Sprintf("tool %q not found", call.Name),
			IsError:    true,
		}, fmt.Errorf("tool %q not found", call.Name)
	}

	// 校验参数格式
	args := call.Arguments
	if len(args) == 0 {
		args = json.RawMessage("{}")
	}
	if err := ValidateArguments(t.Schema(), args); err != nil {
		return gateway.ToolResult{
			ToolCallID: call.ID,
			Name:       call.Name,
			Content:    fmt.Sprintf("invalid arguments for tool %q: %v", call.Name, err),
			IsError:    true,
		}, fmt.Errorf("invalid arguments: %w", err)
	}

	output, err := t.Execute(ctx, args)
	if err != nil {
		return gateway.ToolResult{
			ToolCallID: call.ID,
			Name:       call.Name,
			Content:    err.Error(),
			IsError:    true,
		}, err
	}

	return gateway.ToolResult{
		ToolCallID: call.ID,
		Name:       call.Name,
		Content:    output,
		IsError:    false,
	}, nil
}
