package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
)

// MemoryAppender 是 Agent 向长期记忆追加条目的最小能力。
//
// 刻意定义成只有一个方法的接口，而不是直接依赖 memory 包：
// agent 因此不依赖 memory / dao / gin，装配在 router 层完成。
// 由 memory.Store 实现。
type MemoryAppender interface {
	AppendPending(ctx context.Context, userID, note string) error
}

// RememberToolName 是记忆追加工具名。
const RememberToolName = "remember"

// rememberTool 让模型主动记录学生的稳定信息。
type rememberTool struct {
	appender MemoryAppender
}

// NewRememberTool 构造 remember 工具。
// appender 为 nil 时不注册该工具（未启用记忆能力的环境）。
func NewRememberTool(appender MemoryAppender) tool.InvokableTool {
	if appender == nil {
		return nil
	}
	return &rememberTool{appender: appender}
}

// Info 返回工具元信息，这就是模型看到的「工具说明书」。
// 计划要求工具用法由 Schema 承担，静态 Prompt 里不写参数说明。
func (t *rememberTool) Info(_ context.Context) (*schema.ToolInfo, error) {
	return &schema.ToolInfo{
		Name: RememberToolName,
		Desc: "记录关于学生的长期稳定信息，写入跨会话生效的记忆档案。" +
			"只在了解到学习背景、长期目标、学习偏好、薄弱知识点或明确交互约定时调用。" +
			"不要记录一次性问答、临时话题或整段对话。",
		ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
			"note": {
				Type:     schema.String,
				Desc:     "一条简短、自包含的事实描述，例如「偏好先看可运行代码再看原理」。",
				Required: true,
			},
		}),
	}, nil
}

// InvokableRun 追加一条待整合条目。
//
// UserID 从 context 的 Scope 读取，模型无法通过参数指定其他用户，
// 这是权限边界的一部分。
func (t *rememberTool) InvokableRun(ctx context.Context, argumentsInJSON string, _ ...tool.Option) (string, error) {
	args, err := parseRememberArgs(argumentsInJSON)
	if err != nil {
		return "", err
	}

	scope, ok := ScopeFrom(ctx)
	if !ok || strings.TrimSpace(scope.UserID) == "" {
		return "", fmt.Errorf("remember: 缺少用户上下文，拒绝写入")
	}

	if strings.TrimSpace(args.Note) == "" {
		return "", fmt.Errorf("remember: note 不能为空")
	}

	if err := t.appender.AppendPending(ctx, scope.UserID, args.Note); err != nil {
		return "", fmt.Errorf("remember: 写入记忆失败: %w", err)
	}

	return fmt.Sprintf("已记录：%s（时间 %s）", args.Note, time.Now().Format("2006-01-02")), nil
}

// rememberArgs 是工具入参。
type rememberArgs struct {
	Note string `json:"note"`
}

// parseRememberArgs 解析工具参数。
// 用标准库 json 而非让框架注入结构体，便于单测直接传字符串。
func parseRememberArgs(argumentsInJSON string) (*rememberArgs, error) {
	var a rememberArgs
	raw := strings.TrimSpace(argumentsInJSON)
	if raw == "" || raw == "null" {
		return &a, nil
	}
	if err := jsonUnmarshal(raw, &a); err != nil {
		return nil, fmt.Errorf("remember: 参数解析失败: %w", err)
	}
	return &a, nil
}

// jsonUnmarshal 薄封装，集中一处便于后续替换为 sonic 等更快的实现。
func jsonUnmarshal(data string, v any) error {
	return json.Unmarshal([]byte(data), v)
}

// 编译期断言。
var _ tool.InvokableTool = (*rememberTool)(nil)
