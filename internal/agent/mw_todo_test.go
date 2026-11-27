package agent

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	toolutils "github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
)

func TestHandleWriteTodosConstraints(t *testing.T) {
	if _, err := handleWriteTodos(t.Context(), writeTodosInput{
		Todos: []todoItem{
			{Content: "step 1", Status: "in_progress"},
			{Content: "step 2", Status: "in_progress"},
		},
	}); err == nil || !strings.Contains(err.Error(), "in_progress") {
		t.Fatalf("应拦截多个 in_progress: %v", err)
	}

	many := make([]todoItem, maxTodoItems+1)
	for i := range many {
		many[i] = todoItem{Content: "item", Status: "pending"}
	}
	if _, err := handleWriteTodos(t.Context(), writeTodosInput{Todos: many}); err == nil {
		t.Fatal("应拦截超过 20 项待办")
	}
	if _, err := handleWriteTodos(t.Context(), writeTodosInput{Todos: []todoItem{{Content: " ", Status: "pending"}}}); err == nil {
		t.Fatal("应拦截空 content")
	}
	if _, err := handleWriteTodos(t.Context(), writeTodosInput{Todos: []todoItem{{Content: "ok", Status: "weird"}}}); err == nil {
		t.Fatal("应拦截非法 status")
	}

	out, err := handleWriteTodos(t.Context(), writeTodosInput{
		Todos: []todoItem{
			{Content: "设计大纲", Status: "completed"},
			{Content: "编写模块", Status: "in_progress"},
			{Content: "校验产物", Status: "pending"},
		},
	})
	if err != nil {
		t.Fatalf("合法待办报错: %v", err)
	}
	for _, want := range []string{"[x] 设计大纲", "[>] 编写模块", "[ ] 校验产物", "1/3"} {
		if !strings.Contains(out, want) {
			t.Fatalf("输出缺少 %q: %s", want, out)
		}
	}
}

type todoScriptModel struct {
	step        int
	sawReminder bool
}

func (m *todoScriptModel) WithTools([]*schema.ToolInfo) (model.ToolCallingChatModel, error) {
	return m, nil
}
func (m *todoScriptModel) Generate(_ context.Context, input []*schema.Message, _ ...model.Option) (*schema.Message, error) {
	m.step++
	for _, msg := range input {
		if strings.Contains(msg.Content, todoReminderTag) {
			m.sawReminder = true
		}
	}
	switch m.step {
	case 1:
		args, _ := json.Marshal(writeTodosInput{
			Todos: []todoItem{
				{Content: "步骤一", Status: "in_progress"},
				{Content: "步骤二", Status: "pending"},
			},
		})
		return schema.AssistantMessage("", []schema.ToolCall{{
			ID: "todo-1", Type: "function", Function: schema.FunctionCall{Name: "write_todos", Arguments: string(args)},
		}}), nil
	case 2, 3, 4:
		return schema.AssistantMessage("", []schema.ToolCall{{
			ID: "noop-" + string(rune('0'+m.step)), Type: "function", Function: schema.FunctionCall{Name: "noop", Arguments: `{}`},
		}}), nil
	default:
		return schema.AssistantMessage("全部完成", nil), nil
	}
}
func (m *todoScriptModel) Stream(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	msg, err := m.Generate(ctx, input, opts...)
	if err != nil {
		return nil, err
	}
	return schema.StreamReaderFromArray([]*schema.Message{msg}), nil
}

func TestTodoNagReminderAfterThreshold(t *testing.T) {
	noopTool, err := toolutils.InferTool("noop", "noop", func(context.Context, struct{}) (string, error) { return "ok", nil })
	if err != nil {
		t.Fatal(err)
	}
	todoMW, err := newTodo()
	if err != nil {
		t.Fatal(err)
	}
	mdl := &todoScriptModel{}
	a, err := adk.NewChatModelAgent(t.Context(), &adk.ChatModelAgentConfig{
		Name:        "test-todo-nag",
		Model:       mdl,
		ToolsConfig: adk.ToolsConfig{ToolsNodeConfig: compose.ToolsNodeConfig{Tools: []tool.BaseTool{noopTool}}},
		Handlers:    []adk.ChatModelAgentMiddleware{todoMW},
	})
	if err != nil {
		t.Fatal(err)
	}
	runAgentOnce(t, a, "执行多步任务")
	if !mdl.sawReminder {
		t.Fatal("连续 3 步未更新 write_todos 时应注入 Nag Reminder")
	}
}
