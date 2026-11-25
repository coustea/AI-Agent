package middlewares

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/reduction"
	"github.com/cloudwego/eino/schema"
)

// newReduction 构建官方 Reduction 中间件：外层将 >24KB 工具输出卸载到 /workspace/.offload，
// 调模型前超阈值时清理旧工具结果并压缩 write_file/edit_file 大入参。
// read_file / read_attachment / skill 本身用于按需阅读，不做截断；skill 正文在 Clear 阶段同样保留。
func newReduction(ctx context.Context, cfg Config) (adk.ChatModelAgentMiddleware, error) {
	keepTurns := cfg.HistoryToolTurns
	if keepTurns <= 0 {
		keepTurns = 2
	}
	writeClear := &reduction.ToolReductionConfig{Backend: cfg.Backend, ClearHandler: clearWriteToolArg}
	mw, err := reduction.New(ctx, &reduction.Config{
		Backend:                   cfg.Backend,
		ReadFileToolName:          "read_file",
		RootDir:                   cfg.MountWorkspace + "/.offload",
		MaxLengthForTrunc:         24576,
		TruncExcludeTools:         []string{cfg.ReadAttachmentTool, "read_file", "skill"},
		MaxTokensForClear:         int64(cfg.ReduceTriggerTokens),
		ClearRetentionSuffixLimit: keepTurns,
		ClearAtLeastTokens:        6000,
		ClearExcludeTools:         []string{"skill"},
		ToolConfig:                map[string]*reduction.ToolReductionConfig{"write_file": writeClear, "edit_file": writeClear},
	})
	if err != nil {
		return nil, fmt.Errorf("初始化工具结果精简 Middleware 失败: %w", err)
	}
	return mw, nil
}

// clearWriteToolArg 在 reduction Clear 阶段压缩 write_file/edit_file 的大段入参（Eino 默认只清结果不清入参）。
func clearWriteToolArg(_ context.Context, detail *reduction.ToolDetail) (*reduction.ClearResult, error) {
	if detail == nil || detail.ToolArgument == nil || len(detail.ToolArgument.Text) <= 512 {
		return &reduction.ClearResult{NeedClear: false}, nil
	}
	var arg struct {
		FilePath string `json:"file_path"`
	}
	_ = json.Unmarshal([]byte(detail.ToolArgument.Text), &arg)
	compact, err := json.Marshal(map[string]any{"file_path": arg.FilePath, "cleared": true})
	if err != nil {
		return &reduction.ClearResult{NeedClear: false}, nil
	}
	return &reduction.ClearResult{NeedClear: true, ToolArgument: &schema.ToolArgument{Text: string(compact)}, ToolResult: detail.ToolResult}, nil
}
