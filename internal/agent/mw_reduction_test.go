package agent

import (
	"strings"
	"testing"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/schema"
)

func pureToolBatch(id, name, args, result string) []*schema.Message {
	return []*schema.Message{
		schema.AssistantMessage("", []schema.ToolCall{{ID: id, Type: "function", Function: schema.FunctionCall{Name: name, Arguments: args}}}),
		schema.ToolMessage(result, id, schema.WithToolName(name)),
	}
}

func TestReductionPreservesWorkingMemoryBelowThreshold(t *testing.T) {
	budget := newTokenBudget(1000000, 131072, "explorer")
	mw, err := newReductionMiddleware(t.Context(), budget)
	if err != nil {
		t.Fatal(err)
	}
	messages := []*schema.Message{schema.SystemMessage("system"), schema.UserMessage("调研 8 个要点")}
	messages = append(messages, pureToolBatch("s1", "web_search", `{"query":"q1"}`, "结果一")...)
	messages = append(messages, pureToolBatch("s2", "ls", `{"path":"/workspace"}`, "empty")...)
	messages = append(messages, pureToolBatch("s3", "web_search", `{"query":"q2"}`, "结果二")...)

	_, state, err := mw.BeforeModelRewriteState(t.Context(), &adk.ChatModelAgentState{Messages: messages}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if err := validateToolPairs(state.Messages); err != nil {
		t.Fatal(err)
	}
	var sawS1, sawS2, sawS3 bool
	for _, msg := range state.Messages {
		sawS1 = sawS1 || (msg.ToolCallID == "s1" && msg.Content == "结果一")
		sawS2 = sawS2 || (msg.ToolCallID == "s2" && msg.Content == "empty")
		sawS3 = sawS3 || (msg.ToolCallID == "s3" && msg.Content == "结果二")
	}
	if !sawS1 || !sawS2 || !sawS3 {
		t.Fatalf("低于阈值时不应抹除多步工作记忆: s1=%v s2=%v s3=%v", sawS1, sawS2, sawS3)
	}
}

func TestReductionClearsOldResultsAboveThresholdWithoutMutatingOriginal(t *testing.T) {
	_ = adk.SetLanguage(adk.LanguageChinese)
	oldContent := strings.Repeat("old", 10000)
	newContent := strings.Repeat("new", 2000)

	messages := []*schema.Message{schema.SystemMessage("system"), schema.UserMessage("用户原文")}
	messages = append(messages, toolBatch("skill", "skill", "技能正文")...)
	messages = append(messages, pureToolBatch("todo", "write_todos", `{"todos":[]}`, "[x] 步骤一")...)
	messages = append(messages, toolBatch("old", "read_file", oldContent)...)
	messages = append(messages, toolBatch("latest", "read_file", newContent)...)

	origOldMsg := messages[len(messages)-3]
	budget := newTokenBudget(20000, 8192, "tutor")
	mw, err := newReductionMiddleware(t.Context(), budget)
	if err != nil {
		t.Fatal(err)
	}
	_, state, err := mw.BeforeModelRewriteState(t.Context(), &adk.ChatModelAgentState{Messages: messages}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if err := validateToolPairs(state.Messages); err != nil {
		t.Fatal(err)
	}

	var sawSkill, sawTodo, sawOldCall, sawOldCleared, sawLatest bool
	for _, msg := range state.Messages {
		for _, call := range msg.ToolCalls {
			if call.ID == "old" {
				sawOldCall = true
			}
		}
		if msg.ToolCallID == "old" {
			if strings.Contains(msg.Content, "oldold") {
				t.Fatalf("超阈值旧工具大输出未清理: %q", msg.Content)
			}
			sawOldCleared = msg.Content != ""
		}
		sawSkill = sawSkill || msg.Content == "技能正文"
		sawTodo = sawTodo || msg.Content == "[x] 步骤一"
		sawLatest = sawLatest || (msg.ToolCallID == "latest" && msg.Content == newContent)
	}
	if !sawSkill || !sawTodo || !sawOldCall || !sawOldCleared || !sawLatest {
		t.Fatalf("清理结果不符合预期: skill=%v todo=%v oldCall=%v oldCleared=%v latest=%v",
			sawSkill, sawTodo, sawOldCall, sawOldCleared, sawLatest)
	}
	if origOldMsg.Content != oldContent {
		t.Fatal("原始待持久化的 ToolResult 指针被原地修改")
	}
}
