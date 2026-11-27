package agent

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/summarization"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	toolutils "github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
)

func testSummary() *schema.Message {
	return schema.AssistantMessage(strings.Join(summaryFields, "\n无\n")+"\n继续", nil)
}

func toolBatch(id, name, result string) []*schema.Message {
	args := `{}`
	if name == "skill" {
		args = `{"skill":"pptx"}`
	}
	return []*schema.Message{
		schema.AssistantMessage("有效正文", []schema.ToolCall{{ID: id, Type: "function", Function: schema.FunctionCall{Name: name, Arguments: args}}}),
		schema.ToolMessage(result, id, schema.WithToolName(name)),
	}
}

func TestFinalizeRetainsSkillsAcrossCheckpoints(t *testing.T) {
	original := []*schema.Message{schema.SystemMessage("system"), schema.UserMessage("旧任务")}
	original = append(original, toolBatch("skill", "skill", "第一版规范")...)
	original = append(original, schema.UserMessage("当前原文"))
	first, err := finalizeContext(t.Context(), original, testSummary())
	if err != nil {
		t.Fatal(err)
	}
	raw := mustJSON(t, first)
	var restored []*schema.Message
	if err := json.Unmarshal(raw, &restored); err != nil {
		t.Fatal(err)
	}
	restored = append(restored, toolBatch("new-skill", "skill", "最新规范")...)
	restored = append(restored, schema.UserMessage("下一轮原文"))
	second, err := finalizeContext(t.Context(), restored, testSummary())
	if err != nil {
		t.Fatal(err)
	}
	skills := 0
	for _, msg := range second {
		if contextType(msg) == "skills" {
			skills++
			if !strings.Contains(msg.Content, "最新规范") {
				t.Fatal("没有更新技能正文")
			}
		}
	}
	if skills != 1 || second[len(second)-1].Content != "下一轮原文" {
		t.Fatalf("技能重复或当前原文丢失: %+v", second)
	}
	third, err := finalizeContext(t.Context(), append(second, schema.UserMessage("第三轮原文")), testSummary())
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(third[1].Content, "最新规范") {
		t.Fatal("连续压缩丢失技能")
	}
}

type policyTestModel struct {
	summaryCalls, calls int
	summaryLimits       []int
	summary             *schema.Message
	summaryErr          error
	callTool            bool
	inputs              [][]*schema.Message
	limits              []int
}

func (m *policyTestModel) WithTools([]*schema.ToolInfo) (model.ToolCallingChatModel, error) {
	return m, nil
}
func (m *policyTestModel) Generate(_ context.Context, _ []*schema.Message, opts ...model.Option) (*schema.Message, error) {
	m.summaryCalls++
	options := model.GetCommonOptions(nil, opts...)
	if options.MaxTokens != nil {
		m.summaryLimits = append(m.summaryLimits, *options.MaxTokens)
	}
	if m.summaryErr != nil {
		return nil, m.summaryErr
	}
	if m.summary != nil {
		return m.summary, nil
	}
	return testSummary(), nil
}
func (m *policyTestModel) Stream(_ context.Context, input []*schema.Message, opts ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	m.calls++
	m.inputs = append(m.inputs, input)
	options := model.GetCommonOptions(nil, opts...)
	if options.MaxTokens != nil {
		m.limits = append(m.limits, *options.MaxTokens)
	}
	msg := schema.AssistantMessage("完成", nil)
	if m.callTool && m.calls%2 == 1 {
		msg = toolBatch("echo", "echo", "")[0]
	}
	msg.ResponseMeta = &schema.ResponseMeta{Usage: &schema.TokenUsage{PromptTokens: 10, CompletionTokens: 5, TotalTokens: 15}}
	return schema.StreamReaderFromArray([]*schema.Message{msg}), nil
}

func policyAgent(t *testing.T, m *policyTestModel, window, maxOutput int, tools []tool.BaseTool) (adk.Agent, *tokenBudget) {
	t.Helper()
	budget := newTokenBudget(window, maxOutput, "tutor")
	compaction, err := newContextCompaction(t.Context(), m, budget)
	if err != nil {
		t.Fatal(err)
	}
	a, err := adk.NewChatModelAgent(t.Context(), &adk.ChatModelAgentConfig{
		Name: "policy-test", Instruction: "system", Model: m, MaxIterations: 5,
		ToolsConfig: adk.ToolsConfig{ToolsNodeConfig: compose.ToolsNodeConfig{Tools: tools}},
		Handlers:    []adk.ChatModelAgentMiddleware{budget, compaction},
	})
	if err != nil {
		t.Fatal(err)
	}
	return a, budget
}

func runPolicy(t *testing.T, a adk.Agent, messages []*schema.Message) (checkpoint []*schema.Message, runErr error) {
	t.Helper()
	runner := adk.NewRunner(t.Context(), adk.RunnerConfig{Agent: a, EnableStreaming: true})
	iter := runner.Run(t.Context(), messages)
	for {
		event, ok := iter.Next()
		if !ok {
			break
		}
		if event.Err != nil {
			runErr = event.Err
		}
		if event.Action != nil {
			if action, ok := event.Action.CustomizedAction.(*summarization.CustomizedAction); ok && action.After != nil {
				checkpoint = action.After.Messages
			}
		}
		if event.Output != nil && event.Output.MessageOutput != nil {
			msg := event.Output.MessageOutput
			if msg.IsStreaming {
				sr := msg.MessageStream
				for {
					if _, err := sr.Recv(); err != nil {
						break
					}
				}
				sr.Close()
			}
		}
	}
	return checkpoint, runErr
}

func TestCompactionThresholdBoundary(t *testing.T) {
	messages := []*schema.Message{schema.UserMessage(strings.Repeat("a", 30000)), schema.AssistantMessage("旧回答", nil), schema.UserMessage("当前原文")}
	full := append([]*schema.Message{schema.SystemMessage("system")}, messages...)
	raw, err := estimateTokens(full, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, tokens := range []int64{79900, 80000, 80100} {
		t.Run(fmt.Sprint(tokens), func(t *testing.T) {
			m := &policyTestModel{}
			a, budget := policyAgent(t, m, 100000, 131072, nil)
			budget.scale = float64(tokens) / float64(raw)
			checkpoint, err := runPolicy(t, a, messages)
			if err != nil {
				t.Fatal(err)
			}
			want := 0
			if tokens >= 80000 {
				want = 1
			}
			if want == 1 && (len(m.summaryLimits) != 1 || m.summaryLimits[0] > summaryMaxTokens) {
				t.Fatal("摘要没有受到 8192 输出上限限制")
			}
			if m.summaryCalls != want {
				t.Fatalf("tokens=%d summaryCalls=%d want=%d", tokens, m.summaryCalls, want)
			}
			if want == 1 {
				if len(checkpoint) == 0 || m.inputs[0][len(m.inputs[0])-1].Content != "当前原文" {
					t.Fatal("摘要检查点或当前原文丢失")
				}
				n, err := budget.count(m.inputs[0], nil)
				if err != nil {
					t.Fatal(err)
				}
				if n > 20000 || m.limits[0] != min(131072, 100000-int(n)-1000) {
					t.Fatal("摘要后没有重新统计和限制输出")
				}
			}
		})
	}
}

func TestCompactionOncePerRunAndRearmsNextRun(t *testing.T) {
	long := strings.Repeat("a", 90000)
	echo, err := toolutils.InferTool("echo", "echo", func(context.Context, struct{}) (string, error) { return long, nil })
	if err != nil {
		t.Fatal(err)
	}
	m := &policyTestModel{callTool: true}
	a, _ := policyAgent(t, m, 45000, 131072, []tool.BaseTool{echo})
	messages := []*schema.Message{schema.UserMessage(long), schema.AssistantMessage("历史回答", nil), schema.UserMessage("当前原文")}
	for run := 1; run <= 2; run++ {
		checkpoint, err := runPolicy(t, a, messages)
		if err != nil {
			t.Fatal(err)
		}
		if m.summaryCalls != run || len(checkpoint) == 0 {
			t.Fatalf("run=%d summaries=%d", run, m.summaryCalls)
		}
	}
}

func TestCompactionFailureDoesNotPublishCheckpoint(t *testing.T) {
	for _, tc := range []struct {
		name    string
		summary *schema.Message
		err     error
	}{
		{name: "model-error", err: errors.New("模型不可用")},
		{name: "empty", summary: schema.AssistantMessage("", nil)},
		{name: "invalid-fields", summary: schema.AssistantMessage("没有固定字段", nil)},
		{name: "oversized", summary: schema.AssistantMessage(testSummary().Content+strings.Repeat("大", 5000), nil)},
	} {
		t.Run(tc.name, func(t *testing.T) {
			m := &policyTestModel{summary: tc.summary, summaryErr: tc.err}
			a, _ := policyAgent(t, m, 45000, 131072, nil)
			messages := []*schema.Message{schema.UserMessage(strings.Repeat("a", 90000)), schema.UserMessage("当前原文")}
			before := mustJSON(t, messages)
			checkpoint, err := runPolicy(t, a, messages)
			if err == nil || len(checkpoint) != 0 || m.calls != 0 {
				t.Fatalf("失败摘要生效: err=%v checkpoint=%v", err, checkpoint)
			}
			if !bytes.Equal(before, mustJSON(t, messages)) {
				t.Fatal("失败修改了原上下文")
			}
		})
	}
}

func mustJSON(t *testing.T, v any) []byte {
	t.Helper()
	data, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func TestCompactionRejectsOversizedRetainedContext(t *testing.T) {
	m := &policyTestModel{}
	a, _ := policyAgent(t, m, 45000, 1024, nil)
	messages := []*schema.Message{schema.UserMessage("旧目标"), schema.UserMessage(strings.Repeat("a", 90000))}
	before := mustJSON(t, messages)
	checkpoint, err := runPolicy(t, a, messages)
	if err == nil || !strings.Contains(err.Error(), "20%") || len(checkpoint) > 0 || m.calls != 0 || m.summaryCalls != 1 {
		t.Fatalf("没有拒绝超过目标的保留内容: err=%v", err)
	}
	if !bytes.Equal(before, mustJSON(t, messages)) {
		t.Fatal("目标校验失败后修改了原上下文")
	}
	if len(m.summaryLimits) != 1 || m.summaryLimits[0] != 1024 {
		t.Fatal("摘要未遵守配置输出上限")
	}
}

func TestReductionRunsBeforeCompaction(t *testing.T) {
	m := &policyTestModel{}
	budget := newTokenBudget(45000, 131072, "tutor")
	compaction, err := newContextCompaction(t.Context(), m, budget)
	if err != nil {
		t.Fatal(err)
	}
	reduceMW, err := newReductionMiddleware(t.Context(), budget)
	if err != nil {
		t.Fatal(err)
	}
	a, err := adk.NewChatModelAgent(t.Context(), &adk.ChatModelAgentConfig{
		Name: "prune-first", Instruction: "system", Model: m,
		Handlers: []adk.ChatModelAgentMiddleware{reduceMW, budget, compaction},
	})
	if err != nil {
		t.Fatal(err)
	}
	messages := []*schema.Message{schema.UserMessage("旧目标")}
	messages = append(messages, toolBatch("old", "read_file", strings.Repeat("a", 90000))...)
	messages = append(messages, toolBatch("new", "read_file", "最新结果")...)
	messages = append(messages, schema.UserMessage("当前原文"))
	checkpoint, err := runPolicy(t, a, messages)
	if err != nil || len(checkpoint) > 0 || m.summaryCalls != 0 || m.calls != 1 {
		t.Fatalf("裁剪后不应摘要: %v", err)
	}
	for _, msg := range m.inputs[0] {
		if msg.ToolCallID == "old" && strings.Contains(msg.Content, "aaa") {
			t.Fatal("冗余结果仍在模型输入中")
		}
	}
}

func TestFinalizeValidatesToolAssociations(t *testing.T) {
	original := []*schema.Message{schema.UserMessage("当前请求")}
	broken := toolBatch("call", "read_file", "结果")
	broken[1].ToolCallID = "wrong"
	original = append(original, broken...)
	if _, err := finalizeContext(t.Context(), original, testSummary()); err == nil {
		t.Fatal("摘要接受了缺失关联的工具结果")
	}
}
