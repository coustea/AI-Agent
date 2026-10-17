package tool

import (
	"context"
	"encoding/json"
	"errors"
	"reflect"
	"testing"

	"my-agent/internal/protocol"
)

type mockTool struct {
	name   string
	desc   string
	schema json.RawMessage
	runFn  func(ctx context.Context, args json.RawMessage) (string, error)
}

func (m *mockTool) Name() string            { return m.name }
func (m *mockTool) Description() string     { return m.desc }
func (m *mockTool) Schema() json.RawMessage { return m.schema }
func (m *mockTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	if m.runFn != nil {
		return m.runFn(ctx, args)
	}
	return "ok", nil
}

func TestRegistry_RegisterAndDefinitions(t *testing.T) {
	t1 := &mockTool{
		name:   "tool1",
		desc:   "first tool",
		schema: json.RawMessage(`{"type":"object"}`),
	}
	t2 := &mockTool{
		name:   "tool2",
		desc:   "second tool",
		schema: json.RawMessage(`{"type":"object"}`),
	}

	reg := NewRegistry(t1)
	reg.Register(t2)

	defs := reg.Definitions()
	if len(defs) != 2 {
		t.Fatalf("expected 2 definitions, got %d", len(defs))
	}

	if _, ok := reg.Get("tool1"); !ok {
		t.Errorf("expected tool1 to exist")
	}
	if _, ok := reg.Get("unknown"); ok {
		t.Errorf("expected unknown to not exist")
	}
}

func TestRegistry_Execute(t *testing.T) {
	schema := json.RawMessage(`{
		"type": "object",
		"properties": {
			"query": {"type": "string"}
		},
		"required": ["query"]
	}`)

	t1 := &mockTool{
		name:   "search",
		desc:   "search tool",
		schema: schema,
		runFn: func(ctx context.Context, args json.RawMessage) (string, error) {
			var p struct{ Query string }
			_ = json.Unmarshal(args, &p)
			if p.Query == "fail" {
				return "", errors.New("search failed")
			}
			return "found: " + p.Query, nil
		},
	}

	reg := NewRegistry(t1)
	ctx := context.Background()

	// 1. Tool not found
	res := reg.Execute(ctx, protocol.ToolCall{ID: "1", Name: "nonexistent"})
	if !res.IsError {
		t.Errorf("expected error for nonexistent tool, got res=%+v", res)
	}

	// 2. Missing required parameter
	res = reg.Execute(ctx, protocol.ToolCall{ID: "2", Name: "search", Arguments: `{}`})
	if !res.IsError {
		t.Errorf("expected validation error for missing query, got res=%+v", res)
	}

	// 3. Invalid argument type
	res = reg.Execute(ctx, protocol.ToolCall{ID: "3", Name: "search", Arguments: `{"query": 123}`})
	if !res.IsError {
		t.Errorf("expected type validation error, got res=%+v", res)
	}

	// 4. Execution error
	res = reg.Execute(ctx, protocol.ToolCall{ID: "4", Name: "search", Arguments: `{"query": "fail"}`})
	if !res.IsError || res.Content != "search failed" {
		t.Errorf("expected execution error, got res=%+v", res)
	}

	// 5. Success
	res = reg.Execute(ctx, protocol.ToolCall{ID: "5", Name: "search", Arguments: `{"query": "hello"}`})
	if res.IsError || res.Content != "found: hello" {
		t.Errorf("expected success, got res=%+v", res)
	}
}

// querySchema 要求必须提供字符串型 query，用于构造可预期的参数校验失败。
const querySchema = `{
	"type": "object",
	"properties": {"query": {"type": "string"}},
	"required": ["query"]
}`

// TestRegistry_PreToolUse_OrderAndShortCircuit 验证钩子按挂载顺序执行，且任一返回错误即短路。
func TestRegistry_PreToolUse_OrderAndShortCircuit(t *testing.T) {
	var calls []string

	inner := &mockTool{
		name:   "search",
		schema: json.RawMessage(querySchema),
		runFn: func(ctx context.Context, args json.RawMessage) (string, error) {
			calls = append(calls, "tool")
			return "executed", nil
		},
	}

	reg := NewRegistry(inner)
	reg.UsePreToolUse(nil) // 空钩子应被忽略，且不得 panic

	reg.UsePreToolUse(func(ctx context.Context, call protocol.ToolCall) error {
		calls = append(calls, "hook1")
		return nil
	})
	reg.UsePreToolUse(func(ctx context.Context, call protocol.ToolCall) error {
		calls = append(calls, "hook2")
		return errors.New("blocked by hook2")
	})
	reg.UsePreToolUse(func(ctx context.Context, call protocol.ToolCall) error {
		calls = append(calls, "hook3")
		return nil
	})

	res := reg.Execute(context.Background(), protocol.ToolCall{
		ID: "1", Name: "search", Arguments: `{"query": "hi"}`,
	})
	if !res.IsError || res.Content != "blocked by hook2" {
		t.Errorf("expected blocked ToolResult carrying the hook error, got %+v", res)
	}
	if want := []string{"hook1", "hook2"}; !reflect.DeepEqual(calls, want) {
		t.Errorf("expected hooks to run in order and short-circuit, got %v", calls)
	}
}

// TestRegistry_PreToolUse_AllowThenExecute 验证钩子放行时工具正常执行。
func TestRegistry_PreToolUse_AllowThenExecute(t *testing.T) {
	ran := false
	inner := &mockTool{
		name:   "search",
		schema: json.RawMessage(querySchema),
		runFn: func(ctx context.Context, args json.RawMessage) (string, error) {
			ran = true
			return "ok", nil
		},
	}

	reg := NewRegistry(inner)
	reg.UsePreToolUse(func(ctx context.Context, call protocol.ToolCall) error { return nil })

	res := reg.Execute(context.Background(), protocol.ToolCall{
		ID: "1", Name: "search", Arguments: `{"query": "hi"}`,
	})
	if res.IsError || res.Content != "ok" {
		t.Errorf("expected successful execution, got res=%+v", res)
	}
	if !ran {
		t.Error("expected the tool to be executed when hooks allow it")
	}
}

// TestRegistry_PreToolUse_SeesRawCallBeforeValidation 验证钩子先于参数校验，
// 看到的是未经校验的原始调用。
func TestRegistry_PreToolUse_SeesRawCallBeforeValidation(t *testing.T) {
	var seen protocol.ToolCall
	inner := &mockTool{name: "search", schema: json.RawMessage(querySchema)}

	reg := NewRegistry(inner)
	reg.UsePreToolUse(func(ctx context.Context, call protocol.ToolCall) error {
		seen = call
		return nil
	})

	call := protocol.ToolCall{ID: "1", Name: "search", Arguments: `{"query": 123}`}
	if res := reg.Execute(context.Background(), call); !res.IsError {
		t.Fatal("expected a validation error for the wrong argument type")
	}
	if seen.ID != call.ID || seen.Arguments != call.Arguments {
		t.Errorf("hook did not observe the raw call before validation, got %+v", seen)
	}
}

// TestRegistry_PreToolUse_NoHooks_Regression 回归保护：未挂载钩子时行为与改动前一致。
func TestRegistry_PreToolUse_NoHooks_Regression(t *testing.T) {
	ran := false
	inner := &mockTool{
		name:   "search",
		schema: json.RawMessage(querySchema),
		runFn: func(ctx context.Context, args json.RawMessage) (string, error) {
			ran = true
			return "ok", nil
		},
	}

	reg := NewRegistry(inner)
	res := reg.Execute(context.Background(), protocol.ToolCall{
		ID: "1", Name: "search", Arguments: `{"query": "hi"}`,
	})
	if res.IsError || res.Content != "ok" || !ran {
		t.Errorf("behavior changed without hooks: res=%+v ran=%v", res, ran)
	}
}

// TestRegistry_PostToolUse_ModifiesResult 验证后置钩子能够观察并改写执行结果
func TestRegistry_PostToolUse_ModifiesResult(t *testing.T) {
	inner := &mockTool{
		name:   "search",
		schema: json.RawMessage(querySchema),
		runFn: func(ctx context.Context, args json.RawMessage) (string, error) {
			return "raw output", nil
		},
	}

	reg := NewRegistry(inner)
	reg.UsePostToolUse(func(ctx context.Context, call protocol.ToolCall, result *protocol.ToolResult) {
		if result.Content == "raw output" {
			result.Content = "rewritten output"
		}
	})

	res := reg.Execute(context.Background(), protocol.ToolCall{
		ID: "call_1", Name: "search", Arguments: `{"query":"hi"}`,
	})
	if res.Content != "rewritten output" {
		t.Errorf("expected rewritten output, got %q", res.Content)
	}
}

// TestRegistry_PostToolUse_ExecutionError 验证执行失败时后置钩子依然被调用
func TestRegistry_PostToolUse_ExecutionError(t *testing.T) {
	inner := &mockTool{
		name:   "search",
		schema: json.RawMessage(querySchema),
		runFn: func(ctx context.Context, args json.RawMessage) (string, error) {
			return "", errors.New("boom")
		},
	}

	var seenResult *protocol.ToolResult
	reg := NewRegistry(inner)
	reg.UsePostToolUse(func(ctx context.Context, call protocol.ToolCall, result *protocol.ToolResult) {
		seenResult = result
	})

	res := reg.Execute(context.Background(), protocol.ToolCall{
		ID: "call_2", Name: "search", Arguments: `{"query":"hi"}`,
	})
	if seenResult == nil || !seenResult.IsError || seenResult.Content != "boom" {
		t.Errorf("post hook did not observe the error result: %+v", seenResult)
	}
	if !res.IsError || res.Content != "boom" {
		t.Errorf("expected error result: %+v", res)
	}
}
