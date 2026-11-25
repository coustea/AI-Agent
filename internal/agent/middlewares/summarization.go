package middlewares

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/summarization"
	"github.com/cloudwego/eino/schema"
)

const tutorSummaryInstruction = `关键：仅以纯文本响应，严禁调用任何工具。你的整个回复必须包含一个 <analysis> 块后紧跟一个 <summary> 块。

请将以上教学与创作对话压缩为一份高密度、可无缝续接的中文摘要。请务必准确保留：
1. 学习目标、已讲解并掌握的知识点，以及尚未解决的疑问；
2. 本会话涉及的附件信息（附件 ID、原始文件名、/workspace/... 路径及关键结论）；
3. 工作区 /workspace 下已生成或修改的文件及当前状态；
4. 遇到过的报错、用户的明确偏好或纠正意见；
5. 所有非工具结果的用户消息，完整包裹在 <all_user_messages>...</all_user_messages> 块中；
6. 当前正在进行的任务与下一步计划。

输出格式：
<analysis>
[按时间顺序梳理关键请求、结论、附件与文件状态]
</analysis>

<summary>
1. 主要请求与学习目标：
2. 已掌握知识点与核心结论：
3. 附件与工作区产物：
4. 报错、修正与用户偏好：
5. 所有用户消息：
<all_user_messages>
    - [用户消息]
</all_user_messages>
6. 待完成任务与下一步：
</summary>`

// newSummarization 构建官方 Summarization 中间件：紧接 reduction 后，仍超阈值时压缩摘要并保留已加载的 skill 消息。
// EmitInternalEvents=true 让外层流消费者能捕获压缩后的消息列表并持久化为检查点。
func newSummarization(ctx context.Context, cfg Config) (adk.ChatModelAgentMiddleware, error) {
	finalizer, err := summarization.NewFinalizer().PreserveSkills(&summarization.PreserveSkillsConfig{}).Build()
	if err != nil {
		return nil, fmt.Errorf("初始化上下文压缩 Finalizer 失败: %w", err)
	}
	summaryRetries := 2
	mw, err := summarization.New(ctx, &summarization.Config{
		EmitInternalEvents: true,
		Model:              cfg.Model,
		Trigger:            &summarization.TriggerCondition{ContextTokens: cfg.SummaryTriggerTokens, ContextMessages: cfg.SummaryTriggerMessages},
		UserInstruction:    tutorSummaryInstruction,
		Finalize:           finalizer,
		Retry:              &summarization.RetryConfig{MaxRetries: &summaryRetries, ShouldRetry: newSummaryShouldRetry(cfg.IsTransient)},
	})
	if err != nil {
		return nil, fmt.Errorf("初始化上下文压缩 Middleware 失败: %w", err)
	}
	return mw, nil
}

// newSummaryShouldRetry 判定摘要生成调用是否可重试：仅重试瞬时错误或空摘要，尊重取消与超时。
func newSummaryShouldRetry(isTransient func(error) bool) func(context.Context, *schema.Message, error) bool {
	return func(ctx context.Context, resp *schema.Message, err error) bool {
		if ctx.Err() != nil {
			return false
		}
		if err != nil {
			if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
				return false
			}
			return isTransient != nil && isTransient(err)
		}
		return resp == nil || strings.TrimSpace(resp.Content) == ""
	}
}
