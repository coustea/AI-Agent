// Package agent 的任务规划与防遗忘提醒中间件（todoMiddleware）。
//
// 职责：
//   - 在构造期预构建无状态的 write_todos 工具（避免每次对话请求在 BeforeAgent 重复反射生成 Schema），
//     并强校验服务端约束（最多 20 项、同一时刻最多 1 项 in_progress、合法状态枚举）；
//   - 当存在未完成待办且连续 3 次模型调用未刷新进度时，向本轮运行态末条消息副本追加一次性 <reminder> 提醒。
//
// 关键不变量：
//   - 提醒仅注入到浅拷贝后的模型输入副本，绝不修改原始消息指针，避免污染持久化 Transcript；
//   - 所有进度状态（是否存在未完成项、连续未更新步数）均存在 RunLocal 中，跨请求完全隔离。
package agent

import (
	"context"
	"fmt"
	"strings"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/schema"
)

const (
	maxTodoItems      = 20
	todoNagThreshold  = 3
	todoHasPendingKey = "mentorly:todo_has_pending"
	todoRoundsKey     = "mentorly:todo_rounds"
	todoReminderTag   = "<reminder>你已连续多步未更新任务进度，请调用 write_todos 同步已完成项并保持当前仅有一项 in_progress。</reminder>"
)

// todoItem 定义 write_todos 单条任务结构，jsonschema 标签驱动官方 InferTool 生成参数协议。
type todoItem struct {
	Content    string `json:"content" jsonschema:"description=任务内容描述（非空）"`
	ActiveForm string `json:"activeForm,omitempty" jsonschema:"description=进行中展示文案"`
	Status     string `json:"status" jsonschema:"enum=pending,enum=in_progress,enum=completed,description=任务状态"`
}

// writeTodosInput 每次提交完整任务清单，避免维护易漂移的增量补丁存储。
type writeTodosInput struct {
	Todos []todoItem `json:"todos" jsonschema:"description=完整任务清单（最多 20 项，同时仅允许 1 项为 in_progress）"`
}

type todoMiddleware struct {
	*adk.BaseChatModelAgentMiddleware
	tool tool.BaseTool
}

var _ adk.ChatModelAgentMiddleware = (*todoMiddleware)(nil)

// newTodo 预构建无状态的 write_todos 工具实例供所有会话并发复用。
func newTodo() (*todoMiddleware, error) {
	tl, err := utils.InferTool(
		"write_todos",
		"管理多步骤任务清单。3 步以上或复杂交付任务先列出清单，开始一项标为 in_progress（同一时刻仅允许 1 项），完成后立即更新为 completed；简单问答无需调用。",
		handleWriteTodos,
	)
	if err != nil {
		return nil, fmt.Errorf("初始化 write_todos 工具失败: %w", err)
	}
	return &todoMiddleware{
		BaseChatModelAgentMiddleware: &adk.BaseChatModelAgentMiddleware{},
		tool:                         tl,
	}, nil
}

// BeforeAgent 将预构建的 write_todos 追加到本轮工具切片副本中。
func (t *todoMiddleware) BeforeAgent(ctx context.Context, runCtx *adk.ChatModelAgentContext) (context.Context, *adk.ChatModelAgentContext, error) {
	if runCtx == nil {
		return ctx, nil, nil
	}
	next := *runCtx
	next.Tools = append(append([]tool.BaseTool(nil), runCtx.Tools...), t.tool)
	return ctx, &next, nil
}

// handleWriteTodos 校验完整清单并刷新 RunLocal 待办状态与未更新步数计数。
func handleWriteTodos(ctx context.Context, in writeTodosInput) (string, error) {
	if len(in.Todos) > maxTodoItems {
		return "", fmt.Errorf("待办清单最多 %d 项，当前 %d 项，请合并过细步骤", maxTodoItems, len(in.Todos))
	}

	inProgress, completed, hasPending := 0, 0, false
	var sb strings.Builder
	for i, item := range in.Todos {
		content := strings.TrimSpace(item.Content)
		if content == "" {
			return "", fmt.Errorf("第 %d 项任务 content 不能为空", i+1)
		}
		var mark string
		switch item.Status {
		case "completed":
			mark = "[x]"
			completed++
		case "in_progress":
			mark = "[>]"
			inProgress++
			hasPending = true
		case "pending":
			mark = "[ ]"
			hasPending = true
		default:
			return "", fmt.Errorf("第 %d 项任务 status=%q 无效，仅支持 pending / in_progress / completed", i+1, item.Status)
		}
		fmt.Fprintf(&sb, "%s %s\n", mark, content)
	}
	if inProgress > 1 {
		return "", fmt.Errorf("同一时刻最多只允许 1 项任务处于 in_progress（当前 %d 项），请聚焦当前步骤", inProgress)
	}

	_ = adk.SetRunLocalValue(ctx, todoHasPendingKey, hasPending)
	_ = adk.SetRunLocalValue(ctx, todoRoundsKey, 0)

	if len(in.Todos) == 0 {
		return "已清空待办清单。", nil
	}
	fmt.Fprintf(&sb, "\n进度：%d/%d 已完成", completed, len(in.Todos))
	return sb.String(), nil
}

// BeforeModelRewriteState 累计存在未完成待办时的连续模型调用次数，达到阈值后向末条消息副本追加提醒。
func (t *todoMiddleware) BeforeModelRewriteState(ctx context.Context, state *adk.ChatModelAgentState, _ *adk.ModelContext) (context.Context, *adk.ChatModelAgentState, error) {
	if state == nil || len(state.Messages) == 0 {
		return ctx, state, nil
	}
	pending, _, err := adk.GetRunLocalValue(ctx, todoHasPendingKey)
	if err != nil || pending != true {
		return ctx, state, nil
	}

	rv, _, _ := adk.GetRunLocalValue(ctx, todoRoundsKey)
	rounds, _ := rv.(int)
	rounds++
	_ = adk.SetRunLocalValue(ctx, todoRoundsKey, rounds)

	if rounds < todoNagThreshold {
		return ctx, state, nil
	}
	last := state.Messages[len(state.Messages)-1]
	if last == nil || strings.Contains(last.Content, todoReminderTag) {
		return ctx, state, nil
	}

	msgs := append([]*schema.Message(nil), state.Messages...)
	cp := *last
	cp.Content = strings.TrimRight(cp.Content, "\n") + "\n\n" + todoReminderTag
	msgs[len(msgs)-1] = &cp
	next := *state
	next.Messages = msgs
	return ctx, &next, nil
}
