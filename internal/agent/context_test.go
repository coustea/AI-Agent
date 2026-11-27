package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	toolutils "github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/schema"

	"mentorly/internal/repository/conversations"
)

type checkpointTestModel struct {
	summaryTestModel
	callTool bool
	inputs   [][]*schema.Message
}

func (m *checkpointTestModel) WithTools([]*schema.ToolInfo) (model.ToolCallingChatModel, error) {
	return m, nil
}
func (m *checkpointTestModel) Stream(_ context.Context, input []*schema.Message, _ ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	m.inputs = append(m.inputs, input)
	msg := schema.AssistantMessage("完成", nil)
	if m.callTool {
		m.callTool = false
		msg = schema.AssistantMessage("", []schema.ToolCall{{ID: "echo", Type: "function", Function: schema.FunctionCall{Name: "echo", Arguments: `{}`}}})
	}
	return schema.StreamReaderFromArray([]*schema.Message{msg}), nil
}

func TestMidRunCheckpointRestoresRetainedResultsOnce(t *testing.T) {
	resultText := strings.Repeat("r", 12000)
	echo, err := toolutils.InferTool("echo", "echo", func(context.Context, struct{}) (string, error) { return resultText, nil })
	if err != nil {
		t.Fatal(err)
	}
	// 历史加完整工具定义先低于阈值，工具结果返回后再跨过 80%，验证轮中检查点。
	messages := []*schema.Message{schema.UserMessage("旧问题"), schema.AssistantMessage(strings.Repeat("a", 170000), nil), schema.UserMessage("当前问题原文")}
	m := &checkpointTestModel{callTool: true}
	a, err := New(t.Context(), AgentDeps{Model: m, Tools: []tool.BaseTool{echo}, Config: Config{
		SkillsDir: t.TempDir(), WorkspaceDir: t.TempDir(), ContextWindow: 100000, MaxToken: 131072,
	}})
	if err != nil {
		t.Fatal(err)
	}
	rc := &RunContext{principal: Principal{UserID: "u", ConversationID: "c", Workspace: t.TempDir()}, Messages: messages}
	first := a.Run(t.Context(), rc, nil)
	if first.Status != StatusCompleted || first.Compaction == nil || first.Compaction.CoveredTranscriptCount != 2 || len(first.Transcript) != 2 {
		t.Fatalf("轮中检查点未覆盖保留的工具记录: %+v error=%v", first.Compaction, first.runErr)
	}
	// 保存覆盖边界前的原始记录，再用 JSON 检查点与边界后的最终回答恢复下一轮。
	encoded, err := json.Marshal(first.Compaction.Messages)
	if err != nil {
		t.Fatal(err)
	}
	var restored []*schema.Message
	if err := json.Unmarshal(encoded, &restored); err != nil {
		t.Fatal(err)
	}
	storedFinal := conversations.FromModel(first.Message, conversations.StatusCompleted, true)
	restored = append(restored, conversations.ModelMessages([]conversations.Message{storedFinal})...)
	restored = append(restored, schema.UserMessage("下一轮问题"))
	m.callTool = false
	second := a.Run(t.Context(), &RunContext{principal: rc.principal, Messages: restored}, nil)
	if second.Status != StatusCompleted || second.Compaction != nil {
		t.Fatalf("跨轮恢复失败: %v", second.runErr)
	}
	keptResults := 0
	for _, msg := range m.inputs[len(m.inputs)-1] {
		if msg.Role == schema.Tool && msg.Content == resultText {
			keptResults++
		}
	}
	if keptResults != 1 || m.genCalls.Load() != 1 {
		t.Fatalf("重复恢复近期原文或重复摘要: results=%d summaries=%d", keptResults, m.genCalls.Load())
	}
}

func TestContextErrorsHaveClearUserMessages(t *testing.T) {
	for _, err := range []error{errContextBudget, errContextCompaction} {
		message := userFacingError(fmt.Errorf("模型节点: %w", err))
		if message == "生成失败，请稍后重试" || !strings.Contains(message, "上下文") {
			t.Fatalf("上下文错误未明确反馈: %s", message)
		}
	}
}
