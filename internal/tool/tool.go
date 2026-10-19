package tool

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"

	"my-agent/pkg/llm"
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
	mu        sync.RWMutex
	tools     map[string]Tool
	preHooks  []PreToolUse
	postHooks []PostToolUse
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

// UsePreToolUse 挂载一个执行前钩子。钩子按挂载顺序依次执行，任一返回错误即短路。
// Registry 只负责按序调用，不感知任何具体策略。
func (r *Registry) UsePreToolUse(h PreToolUse) {
	if h == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.preHooks = append(r.preHooks, h)
}

// UsePostToolUse 挂载一个执行后钩子。钩子按挂载顺序依次执行，可观察或改写 ToolResult。
func (r *Registry) UsePostToolUse(h PostToolUse) {
	if h == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.postHooks = append(r.postHooks, h)
}

// Get 根据名称获取工具
func (r *Registry) Get(name string) (Tool, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	t, ok := r.tools[name]
	return t, ok
}

// Definitions 导出供大模型 Function Calling 使用的工具定义列表
func (r *Registry) Definitions() []llm.ToolDefinition {
	r.mu.RLock()
	defer r.mu.RUnlock()

	defs := make([]llm.ToolDefinition, 0, len(r.tools))
	for _, t := range r.tools {
		defs = append(defs, llm.ToolDefinition{
			Name:        t.Name(),
			Description: t.Description(),
			Parameters:  t.Schema(),
		})
	}
	return defs
}

// Execute 校验参数并安全执行对应的工具。
//
// 执行流水线为：查找工具 → 执行前钩子链 (PreToolUse) → 参数校验 → 工具执行 → 执行后钩子链 (PostToolUse)。
// 钩子先于参数校验，看到的是未经校验的原始调用；钩子若无法解析参数应放行，
// 交由参数校验拒绝，避免重复报错。所有失败均以 IsError + Content 表达，不再返回 error。
func (r *Registry) Execute(ctx context.Context, call llm.ToolCall) llm.ToolResult {
	r.mu.RLock()
	t, ok := r.tools[call.Name]
	preHooks := r.preHooks
	postHooks := r.postHooks
	r.mu.RUnlock()

	if !ok {
		return llm.ToolResult{
			ToolCallID: call.ID,
			Name:       call.Name,
			Content:    fmt.Sprintf("tool %q not found", call.Name),
			IsError:    true,
		}
	}

	// 1. 执行前钩子链：权限等策略在此挂载，任一错误即短路拦截
	for _, h := range preHooks {
		if err := h(ctx, call); err != nil {
			return llm.ToolResult{
				ToolCallID: call.ID,
				Name:       call.Name,
				Content:    err.Error(),
				IsError:    true,
			}
		}
	}

	// 2. 校验参数格式
	args := []byte(call.Arguments)
	if len(args) == 0 {
		args = []byte("{}")
	}
	if err := ValidateArguments(t.Schema(), args); err != nil {
		return llm.ToolResult{
			ToolCallID: call.ID,
			Name:       call.Name,
			Content:    fmt.Sprintf("invalid arguments for tool %q: %v", call.Name, err),
			IsError:    true,
		}
	}

	// 3. 工具本体执行（panic 转为 IsError 结果，单工具崩溃不击穿整轮）
	output, err := executeTool(t, ctx, args)
	var res llm.ToolResult
	if err != nil {
		res = llm.ToolResult{
			ToolCallID: call.ID,
			Name:       call.Name,
			Content:    err.Error(),
			IsError:    true,
		}
	} else {
		res = llm.ToolResult{
			ToolCallID: call.ID,
			Name:       call.Name,
			Content:    output,
			IsError:    false,
		}
	}

	// 4. 执行后置钩子链：大结果落盘预览、审计等在此执行，结果可被观察或改写
	for _, h := range postHooks {
		h(ctx, call, &res)
	}

	return res
}

// executeTool 执行工具并捕获 panic，将其转为普通错误返回
func executeTool(t Tool, ctx context.Context, args json.RawMessage) (output string, err error) {
	defer func() {
		if r := recover(); r != nil {
			output = ""
			err = fmt.Errorf("tool panicked: %v", r)
		}
	}()
	return t.Execute(ctx, args)
}
