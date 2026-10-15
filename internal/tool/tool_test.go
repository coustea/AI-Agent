package tool

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"my-agent/internal/gateway"
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
	res, err := reg.Execute(ctx, gateway.ToolCall{ID: "1", Name: "nonexistent"})
	if err == nil || !res.IsError {
		t.Errorf("expected error for nonexistent tool, got res=%+v, err=%v", res, err)
	}

	// 2. Missing required parameter
	res, err = reg.Execute(ctx, gateway.ToolCall{ID: "2", Name: "search", Arguments: json.RawMessage(`{}`)})
	if err == nil || !res.IsError {
		t.Errorf("expected validation error for missing query, got res=%+v, err=%v", res, err)
	}

	// 3. Invalid argument type
	res, err = reg.Execute(ctx, gateway.ToolCall{ID: "3", Name: "search", Arguments: json.RawMessage(`{"query": 123}`)})
	if err == nil || !res.IsError {
		t.Errorf("expected type validation error, got res=%+v, err=%v", res, err)
	}

	// 4. Execution error
	res, err = reg.Execute(ctx, gateway.ToolCall{ID: "4", Name: "search", Arguments: json.RawMessage(`{"query": "fail"}`)})
	if err == nil || !res.IsError || res.Content != "search failed" {
		t.Errorf("expected execution error, got res=%+v, err=%v", res, err)
	}

	// 5. Success
	res, err = reg.Execute(ctx, gateway.ToolCall{ID: "5", Name: "search", Arguments: json.RawMessage(`{"query": "hello"}`)})
	if err != nil || res.IsError || res.Content != "found: hello" {
		t.Errorf("expected success, got res=%+v, err=%v", res, err)
	}
}
