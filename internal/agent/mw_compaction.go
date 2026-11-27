// Package agent 的上下文自动摘要中间件（contextCompaction）。
//
// 职责：
//   - 基于 Eino 官方 summarization 中间件驱动摘要模型调用与阶段事件（Before / Generate / After）；
//   - 在前置 reduction 清理旧工具输出后，若剩余上下文仍 >= 窗口 80%，触发单轮最多一次的原子压缩；
//   - 原子验收标准：摘要必须包含 6 个非空固定 Markdown 段落、<= 8192 tokens、保留活动技能正文、
//     保留当前用户原文与最新完整工具调用批次、工具对校验通过且整体 <= 窗口 20%。
//
// 关键不变量：
//   - 任意一步校验失败都必须返回错误并原样保留旧上下文，绝不原地修改 state.Messages；
//   - 通过 RunLocal（compactionUsedKey）限制单轮最多触发一次，防止压缩失败或临界震荡导致无限摘要。
package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/summarization"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"
)

const (
	compactionUsedKey = "mentorly:compaction_used" // RunLocal 标记，仅作用于当前单轮运行。
	contextTypeKey    = "mentorly:context_type"    // Message.Extra 标记，随检查点持久化区分摘要/技能/真实请求。
	skillNameKey      = "mentorly:skill_name"      // 活动技能唯一名称，供连续多次摘要时按名去重覆盖。
	summaryMaxTokens  = 8192
)

var summaryFields = []string{"## 当前目标", "## 用户约束", "## 已确认事实", "## 执行进度", "## 文件附件", "## 下一步"}

const tutorSummaryInstruction = `仅输出简洁中文 Markdown 摘要，不调用工具。使用以下固定字段，无内容时写“无”：
## 当前目标
## 用户约束
## 已确认事实
## 执行进度
## 文件附件
## 下一步
保留用户纠正、关键事实、未解决错误、附件 ID 和路径、文件状态以及后续工作所需信息。
大幅简化旧对话与重复执行细节，不复制全部用户原文，不输出分析过程。最多 8192 tokens。`

type contextCompaction struct {
	*adk.BaseChatModelAgentMiddleware
	summary *summarization.TypedMiddleware[*schema.Message]
	budget  *tokenBudget
}

// newContextCompaction 复用 Eino summarization 流程，摘要模型调用单独归入 "summary" 用量分组。
func newContextCompaction(ctx context.Context, cm model.BaseChatModel, budget *tokenBudget) (*contextCompaction, error) {
	summaryBudget := newTokenBudget(budget.window, min(summaryMaxTokens, budget.maxOutput), "summary")
	mw, err := summarization.New(ctx, &summarization.Config{
		Model:              &budgetModel{inner: cm, budget: summaryBudget},
		EmitInternalEvents: true, // 让 stream.go 捕获 AfterSummarize 检查点事件。
		UserInstruction:    tutorSummaryInstruction,
		GenModelInput: func(_ context.Context, system, instruction *schema.Message, original []*schema.Message) ([]*schema.Message, error) {
			// 摘要模型使用专用系统指令，剔除原业务 System 后传入历史对话与摘要任务说明。
			input := []*schema.Message{system}
			for _, msg := range original {
				if msg.Role != schema.System {
					input = append(input, msg)
				}
			}
			return append(input, instruction), nil
		},
		Finalize: finalizeContext,
		Callback: func(_ context.Context, _, after adk.ChatModelAgentState) error {
			// 官方在 Finalize 成功之后、发送 AfterSummarize 事件之前执行 Callback；
			// 20% 验收覆盖完整保留上下文（含工具定义），不通过则中止提交。
			n, err := budget.count(after.Messages, after.ToolInfos)
			if err != nil {
				return err
			}
			if n*5 > int64(budget.window) {
				return fmt.Errorf("摘要后上下文 %d tokens 超过窗口 20%% 目标，保留原上下文", n)
			}
			return nil
		},
	})
	if err != nil {
		return nil, err
	}
	return &contextCompaction{
		BaseChatModelAgentMiddleware: &adk.BaseChatModelAgentMiddleware{},
		summary:                      mw.(*summarization.TypedMiddleware[*schema.Message]),
		budget:                       budget,
	}, nil
}

// BeforeModelRewriteState 检查 80% 触发阈值与单轮次数锁，通过后显式调用官方 Summarize。
func (c *contextCompaction) BeforeModelRewriteState(ctx context.Context, state *adk.ChatModelAgentState, _ *adk.ModelContext) (context.Context, *adk.ChatModelAgentState, error) {
	n, err := c.budget.count(state.Messages, state.ToolInfos)
	// 用整数交叉乘法（n*5 < window*4）判断 80%，避免浮点误差。
	if err != nil || n*5 < int64(c.budget.window)*4 {
		return ctx, state, err
	}
	used, _, err := adk.GetRunLocalValue(ctx, compactionUsedKey)
	if err != nil || used == true {
		return ctx, state, err
	}
	// 调用前即占用本轮配额，摘要失败也不在同一轮反复重试。
	if err := adk.SetRunLocalValue(ctx, compactionUsedKey, true); err != nil {
		return ctx, state, err
	}
	messages, err := c.summary.Summarize(ctx, state)
	if err != nil {
		return ctx, state, fmt.Errorf("%w，保留原上下文: %w", errContextCompaction, err)
	}
	next := *state
	next.Messages = messages
	return ctx, &next, nil
}

func contextType(msg *schema.Message) string {
	if msg == nil {
		return ""
	}
	kind, _ := msg.Extra[contextTypeKey].(string)
	return kind
}

// finalizeContext 以纯函数方式拼装压缩后的新消息序列：
// [System...] + [去重后的活动技能...] + [结构化摘要] + [当前用户请求 与 最新非技能工具批次（保持原有先后）]。
func finalizeContext(_ context.Context, original []*schema.Message, summary *schema.Message) ([]*schema.Message, error) {
	if err := validateSummaryContent(summary); err != nil {
		return nil, err
	}

	systems, skills, current, latestBatch, err := scanOriginalContext(original)
	if err != nil {
		return nil, err
	}
	if current < 0 {
		return nil, fmt.Errorf("无法定位当前用户请求")
	}

	latest, err := extractLatestToolBatch(original, latestBatch)
	if err != nil {
		return nil, err
	}

	out := make([]*schema.Message, 0, len(systems)+len(skills)+1+len(latest)+1)
	out = append(out, systems...)
	out = append(out, skills...)
	out = append(out, &schema.Message{
		Role:    schema.User,
		Content: summary.Content,
		Extra:   map[string]any{contextTypeKey: "summary"},
	})
	if latestBatch >= 0 && latestBatch < current {
		out = append(out, latest...)
	}
	out = append(out, original[current])
	if latestBatch > current {
		out = append(out, latest...)
	}
	return out, validateToolPairs(out)
}

// validateSummaryContent 校验摘要模型输出为非空纯文本、不超 8192 tokens 且严格包含 6 个非空固定段落。
func validateSummaryContent(summary *schema.Message) error {
	if summary == nil || strings.TrimSpace(summary.Content) == "" || len(summary.ToolCalls) > 0 || len(summary.AssistantGenMultiContent) > 0 {
		return fmt.Errorf("摘要必须为非空 Markdown 正文")
	}
	if estimateText(summary.Content) > summaryMaxTokens {
		return fmt.Errorf("摘要正文超过 8192 tokens 估算上限")
	}
	remaining := strings.TrimSpace(summary.Content)
	for i, field := range summaryFields {
		if !strings.HasPrefix(remaining, field+"\n") {
			return fmt.Errorf("摘要缺少固定字段 %s", field)
		}
		remaining = strings.TrimPrefix(remaining, field+"\n")
		content := remaining
		if i+1 < len(summaryFields) {
			var found bool
			content, remaining, found = strings.Cut(remaining, summaryFields[i+1]+"\n")
			if !found {
				return fmt.Errorf("摘要缺少固定字段 %s", summaryFields[i+1])
			}
			remaining = summaryFields[i+1] + "\n" + remaining
		}
		if strings.TrimSpace(content) == "" {
			return fmt.Errorf("摘要字段 %s 不能为空", field)
		}
	}
	return nil
}

// scanOriginalContext 一次遍历提取 System、按名去重的活动技能正文、最后一条真实用户消息下标与最新工具批次下标。
func scanOriginalContext(original []*schema.Message) (systems, skills []*schema.Message, current, latestBatch int, err error) {
	skillMap := make(map[string]*schema.Message)
	var skillOrder []string
	keepSkill := func(name string, msg *schema.Message) {
		if _, exists := skillMap[name]; !exists {
			skillOrder = append(skillOrder, name)
		}
		skillMap[name] = msg
	}

	skillCalls := make(map[string]string) // ToolCallID -> skill name
	current, latestBatch = -1, -1

	for i, msg := range original {
		if msg.Role == schema.System {
			systems = append(systems, msg)
		}
		if contextType(msg) == "skills" {
			name, _ := msg.Extra[skillNameKey].(string)
			keepSkill(name, msg)
		}
		// 带 contextType 标记的 User 消息属于保留技能或历史摘要，不能误认作真实用户请求。
		if msg.Role == schema.User && contextType(msg) == "" {
			current = i
		}
		if len(msg.ToolCalls) > 0 {
			latestBatch = i
		}
		for _, call := range msg.ToolCalls {
			if call.Function.Name != "skill" {
				continue
			}
			var arg struct {
				Skill string `json:"skill"`
			}
			if err := json.Unmarshal([]byte(call.Function.Arguments), &arg); err != nil || arg.Skill == "" {
				return nil, nil, -1, -1, fmt.Errorf("技能调用参数无效: %s", call.ID)
			}
			skillCalls[call.ID] = arg.Skill
		}
		if name, ok := skillCalls[msg.ToolCallID]; ok && msg.Role == schema.Tool {
			// 将技能工具结果提升为独立保留消息，脱离即将被压缩的调用链。
			preserved := *msg
			preserved.Role, preserved.ToolCallID, preserved.ToolName = schema.User, "", ""
			preserved.Content = "活动技能 " + name + "\n" + msg.Content
			preserved.Extra = map[string]any{contextTypeKey: "skills", skillNameKey: name}
			keepSkill(name, &preserved)
		}
	}

	skills = make([]*schema.Message, 0, len(skillOrder))
	for _, name := range skillOrder {
		skills = append(skills, skillMap[name])
	}
	return systems, skills, current, latestBatch, nil
}

// extractLatestToolBatch 复制最新一批非技能工具调用及其完整结果；不修改原消息切片以保证失败可回滚。
func extractLatestToolBatch(original []*schema.Message, latestBatch int) ([]*schema.Message, error) {
	if latestBatch < 0 {
		return nil, nil
	}
	end := latestBatch + 1 + len(original[latestBatch].ToolCalls)
	if end > len(original) {
		return nil, fmt.Errorf("最新工具记录不完整")
	}
	call := *original[latestBatch]
	call.ToolCalls = nil
	ids := make(map[string]bool)
	for _, tc := range original[latestBatch].ToolCalls {
		if tc.Function.Name != "skill" {
			call.ToolCalls = append(call.ToolCalls, tc)
			ids[tc.ID] = true
		}
	}
	var latest []*schema.Message
	if len(call.ToolCalls) > 0 {
		latest = append(latest, &call)
	}
	for _, result := range original[latestBatch+1 : end] {
		if ids[result.ToolCallID] {
			latest = append(latest, result)
		}
	}
	return latest, nil
}

// validateToolPairs 强制每批 ToolCalls 后紧跟且仅跟对应的完整 Tool 结果，拒绝孤立、缺失或重复 ID。
func validateToolPairs(messages []*schema.Message) error {
	pending := make(map[string]bool)
	for _, msg := range messages {
		if msg == nil {
			return fmt.Errorf("上下文含空消息")
		}
		if msg.Role == schema.Tool {
			if !pending[msg.ToolCallID] {
				return fmt.Errorf("工具结果缺少关联调用: %s", msg.ToolCallID)
			}
			delete(pending, msg.ToolCallID)
			continue
		}
		if len(pending) > 0 {
			return fmt.Errorf("工具调用缺少完整结果")
		}
		for _, call := range msg.ToolCalls {
			if call.ID == "" || pending[call.ID] {
				return fmt.Errorf("工具调用 ID 为空或重复")
			}
			pending[call.ID] = true
		}
	}
	if len(pending) > 0 {
		return fmt.Errorf("工具调用缺少完整结果")
	}
	return nil
}
