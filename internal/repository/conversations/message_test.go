package conversations

import (
	"encoding/json"
	"reflect"
	"strings"
	"testing"

	"github.com/cloudwego/eino/schema"
)

func TestStoreMessageFiltering(t *testing.T) {
	history := []Message{
		{Role: RoleUser, Content: "问题一", Status: StatusCompleted},
		{Role: RoleAssistant, Content: "", Status: StatusFailed},
		{Role: RoleAssistant, Content: "回答一", Status: StatusCompleted},
	}

	kept := ModelMessages(history)
	if len(kept) != 2 {
		t.Fatalf("保留 %d 条, 期望 2", len(kept))
	}
	if kept[1].Content != "回答一" {
		t.Errorf("第二条 = %q", kept[1].Content)
	}
	if kept[0].Role != schema.User || kept[1].Role != schema.Assistant {
		t.Errorf("角色映射错误: %v / %v", kept[0].Role, kept[1].Role)
	}
}

func TestToSchemaMessagesKeepsToolCalls(t *testing.T) {
	history := []Message{
		FromModel(schema.AssistantMessage("", []schema.ToolCall{{ID: "call-1"}}), StatusCompleted, false),
	}

	kept := ModelMessages(history)
	if len(kept) != 1 {
		t.Fatalf("带工具调用的消息被误删, 保留 %d 条", len(kept))
	}
	if len(kept[0].ToolCalls) != 1 || kept[0].ToolCalls[0].ID != "call-1" {
		t.Errorf("工具调用未保留: %+v", kept[0])
	}
}

func TestModelMessageRoundTrip(t *testing.T) {
	original := &schema.Message{
		Role:             schema.Assistant,
		Content:          "回答",
		ReasoningContent: "reasoning",
		Extra:            map[string]any{"signature": "opaque"},
		ToolCalls:        []schema.ToolCall{{ID: "call-1", Function: schema.FunctionCall{Name: "read_attachment", Arguments: `{}`}}},
		ResponseMeta:     &schema.ResponseMeta{Usage: &schema.TokenUsage{CompletionTokens: 12}},
	}
	record := FromModel(original, StatusCompleted, true)
	record.ID, record.AttachmentIDs = 7, []string{"attachment-1"}

	data, err := json.Marshal(record.ModelMessage)
	if err != nil {
		t.Fatal(err)
	}
	record.ModelMessage = new(schema.Message)
	if err := json.Unmarshal(data, record.ModelMessage); err != nil {
		t.Fatal(err)
	}
	if record.ModelMessage.ReasoningContent != "reasoning" {
		t.Fatalf("数据库记录不应丢失推理过程: %+v", record.ModelMessage)
	}
	want := *original
	want.ReasoningContent = ""
	restored := ModelMessages([]Message{record})
	if len(restored) != 1 || !reflect.DeepEqual(&want, restored[0]) {
		t.Fatalf("消息恢复错误: got=%+v want=%+v", restored, &want)
	}
	if record.ID != 7 || record.Tokens != 12 || !record.Visible || record.AttachmentIDs[0] != "attachment-1" {
		t.Fatal("业务字段丢失")
	}
	record.Content += "\n附件引用"
	got := ModelMessages([]Message{record})[0]
	if !strings.Contains(got.Content, "附件引用") || original.Content != "回答" {
		t.Fatal("引用装配污染了原始模型消息")
	}
}
