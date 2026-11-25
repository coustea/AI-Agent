// Package middlewares 集中装配 TutorAgent 的全部 Eino ChatModelAgentMiddleware。
//
// Eino deep.New 完整中间件链路（按注册顺序；Wrap* 钩子按洋葱模型，先注册的在最外层）：
//   [内置] write_todos    — BeforeAgent 注入待办规划工具
//   [内置] filesystem     — BeforeAgent 注入 ls/read_file/write_file/edit_file/glob/grep（execute 由 tools/ 独立实现）
//   [内置] task           — BeforeAgent 注入通用子代理工具（deep.New 默认启用）
//   [0]    skill          — BeforeAgent 注入 skill 工具与 /skills 目录说明；WrapModel 挂载技能上下文
//   [1]    patchtoolcalls — BeforeModelRewriteState 补齐历史里中断的悬空 tool_calls
//   [2]    reduction      — Wrap*ToolCall（外层）卸载 >24KB 工具输出到 /workspace/.offload；
//                           BeforeModelRewriteState 超阈值时清理早于近 N 轮的旧工具结果与大写入参数
//   [3]    summarization  — BeforeModelRewriteState（紧接 reduction）超限时生成中文摘要并保留 skill
//   [4]    toolGuard      — Wrap*ToolCall（最内层）拦截高危 shell 命令，将可恢复工具错误转为脱敏反馈
package middlewares

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/adk"
	adkfs "github.com/cloudwego/eino/adk/filesystem"
	"github.com/cloudwego/eino/adk/middlewares/patchtoolcalls"
	"github.com/cloudwego/eino/adk/middlewares/skill"
	"github.com/cloudwego/eino/components/model"
)

// Config 是装配 TutorAgent 中间件链路所需的全部参数。
type Config struct {
	Model                  model.ToolCallingChatModel
	Backend                adkfs.Backend
	MountSkills            string
	MountWorkspace         string
	ReadAttachmentTool     string
	HistoryToolTurns       int
	ReduceTriggerTokens    int
	SummaryTriggerTokens   int
	SummaryTriggerMessages int
	IsTransient            func(error) bool
	ToolGuard              ToolGuardConfig
}

// Build 按生效顺序构建 TutorAgent 的全部 5 个 ChatModelAgentMiddleware。
func Build(ctx context.Context, cfg Config) ([]adk.ChatModelAgentMiddleware, error) {
	// [0] skill：BeforeAgent 注入 skill 工具与技能目录提示。
	skillBackend, err := skill.NewBackendFromFilesystem(ctx, &skill.BackendFromFilesystemConfig{
		Backend: cfg.Backend,
		BaseDir: cfg.MountSkills,
	})
	if err != nil {
		return nil, fmt.Errorf("初始化技能后端失败: %w", err)
	}
	skillMW, err := skill.NewMiddleware(ctx, &skill.Config{Backend: skillBackend})
	if err != nil {
		return nil, fmt.Errorf("初始化技能 Middleware 失败: %w", err)
	}

	// [1] patchtoolcalls：BeforeModelRewriteState 补齐悬空 tool_calls。
	patchMW, err := patchtoolcalls.New(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("初始化 PatchToolCalls Middleware 失败: %w", err)
	}

	// [2] reduction：卸载大输出 + 清理旧工具结果与大写入入参。
	reduceMW, err := newReduction(ctx, cfg)
	if err != nil {
		return nil, err
	}

	// [3] summarization：超阈值生成中文摘要并保留已加载的 skill 消息。
	sumMW, err := newSummarization(ctx, cfg)
	if err != nil {
		return nil, err
	}

	// [4] toolGuard：最内层工具包装，拦截高危命令并把可恢复工具错误转为脱敏反馈。
	guardMW := NewToolGuard(cfg.ToolGuard)

	return []adk.ChatModelAgentMiddleware{skillMW, patchMW, reduceMW, sumMW, guardMW}, nil
}
