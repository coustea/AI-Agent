package service

import (
	"testing"

	"github.com/cloudwego/eino/schema"
	"mentorly/internal/repository/attachments"
)

func TestCompletedToolPairs(t *testing.T) {
	call := &schema.Message{Role: schema.Assistant, ToolCalls: []schema.ToolCall{{ID: "call-1", Function: schema.FunctionCall{Name: "read_file", Arguments: `{}`}}}}
	result := &schema.Message{Role: schema.Tool, ToolCallID: "call-1", ToolName: "read_file", Content: "ok"}
	if got := completedToolPairs([]*schema.Message{call, result}); len(got) != 2 {
		t.Fatalf("完整调用应保存两条消息，得到 %d", len(got))
	}
	if got := completedToolPairs([]*schema.Message{call}); len(got) != 0 {
		t.Fatalf("缺少工具结果时不应保存调用，得到 %d", len(got))
	}
	duplicate := []*schema.Message{call, result, result}
	if got := completedToolPairs(duplicate); len(got) != 0 {
		t.Fatalf("重复工具结果时不应保存调用，得到 %d", len(got))
	}
}

func TestConversationRunLock(t *testing.T) {
	s := &Chat{active: make(map[string]struct{})}
	if !s.acquire("user:conversation") || s.acquire("user:conversation") {
		t.Fatal("同一会话必须只允许一个运行")
	}
	if !s.acquire("user:other") {
		t.Fatal("不同会话应可并发")
	}
	s.release("user:conversation")
	if !s.acquire("user:conversation") {
		t.Fatal("结束后应允许下一轮")
	}
}

// TestOrderedAttachmentsFollowsMessageOrder 附件顺序必须等于消息记录的 ID 顺序。
//
// 这是前端按顺序渲染的唯一依据：用户先传 A 再传 B，
// 前端就必须先画 A。任何按主键、按时间或按 map 遍历的实现都会破坏它。
func TestOrderedAttachmentsFollowsMessageOrder(t *testing.T) {
	byID := map[string]*attachments.Attachment{
		"c": {ID: "c", Filename: "third.pdf"},
		"a": {ID: "a", Filename: "first.png"},
		"b": {ID: "b", Filename: "second.docx"},
	}

	got := orderedAttachments([]string{"a", "b", "c"}, byID)
	if len(got) != 3 {
		t.Fatalf("附件数 = %d, 期望 3", len(got))
	}
	for i, want := range []string{"a", "b", "c"} {
		if got[i].ID != want {
			t.Errorf("第 %d 个附件 = %q, 期望 %q", i, got[i].ID, want)
		}
	}

	// 反过来传参也必须反过来返回：顺序来自消息，不是来自查询结果。
	reversed := orderedAttachments([]string{"c", "b", "a"}, byID)
	if reversed[0].ID != "c" || reversed[2].ID != "a" {
		t.Errorf("顺序未跟随入参: %+v", reversed)
	}
}

// TestOrderedAttachmentsSkipsMissing 附件记录缺失时跳过，不影响其余附件。
//
// 附件被清理后，历史消息仍要能正常展示剩下的附件，
// 而不是整条消息查不出来或渲染成空白。
func TestOrderedAttachmentsSkipsMissing(t *testing.T) {
	byID := map[string]*attachments.Attachment{
		"a": {ID: "a", Filename: "first.png"},
	}

	got := orderedAttachments([]string{"gone", "a", "also-gone"}, byID)
	if len(got) != 1 || got[0].ID != "a" {
		t.Fatalf("缺失附件未被跳过: %+v", got)
	}

	if none := orderedAttachments(nil, byID); none != nil {
		t.Errorf("无附件时应返回 nil，得到 %+v", none)
	}
	if allGone := orderedAttachments([]string{"x"}, byID); allGone != nil {
		t.Errorf("全部缺失时应返回 nil，得到 %+v", allGone)
	}
}

// TestAttachmentIDsOf 落库的附件 ID 必须来自已校验列表，且顺序一致。
//
// 原始请求可能含空串或重复项：直接落库会让前端渲染出空槽位，
// 或者让「附件数」与实际不符。这里统一以校验后的列表为准。
func TestAttachmentIDsOf(t *testing.T) {
	items := []*attachments.Attachment{
		{ID: "a"}, {ID: "b"}, nil, {ID: "  "}, {ID: "c"},
	}
	got := attachmentIDsOf(items)
	want := []string{"a", "b", "c"}
	if len(got) != len(want) {
		t.Fatalf("IDs = %v, 期望 %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("第 %d 个 ID = %q, 期望 %q", i, got[i], want[i])
		}
	}

	if none := attachmentIDsOf(nil); none != nil {
		t.Errorf("无附件时应返回 nil，得到 %v", none)
	}
	if empty := attachmentIDsOf([]*attachments.Attachment{{ID: " "}}); empty != nil {
		t.Errorf("全部为空 ID 时应返回 nil，得到 %v", empty)
	}
}

func TestCompletedToolPairsWithBoundary(t *testing.T) {
	call1 := &schema.Message{Role: schema.Assistant, ToolCalls: []schema.ToolCall{{ID: "c1", Function: schema.FunctionCall{Name: "read_file", Arguments: `{}`}}}}
	res1 := &schema.Message{Role: schema.Tool, ToolCallID: "c1", ToolName: "read_file", Content: "ok1"}
	call2 := &schema.Message{Role: schema.Assistant, ToolCalls: []schema.ToolCall{{ID: "c2", Function: schema.FunctionCall{Name: "execute", Arguments: `{}`}}}}
	res2 := &schema.Message{Role: schema.Tool, ToolCallID: "c2", ToolName: "execute", Content: "ok2"}

	kept, mapped, ok := completedToolPairsWithBoundary([]*schema.Message{call1, res1, call2, res2}, 2)
	if !ok || len(kept) != 4 || mapped != 2 {
		t.Fatalf("合法轮中压缩边界映射错误: kept=%d mapped=%d ok=%v", len(kept), mapped, ok)
	}
	if _, _, ok := completedToolPairsWithBoundary([]*schema.Message{call1, res1, call2}, 3); ok {
		t.Fatal("落在未完成工具对上的压缩边界应判为无效")
	}
}

func TestPrepareRejectsTooManyAttachments(t *testing.T) {
	s := NewChat(nil, nil, 2, nil)
	_, err := s.Prepare(t.Context(), "u1", "c1", "看附件", []string{"a1", "a2", "a3"})
	if err == nil || countUniqueAttachmentIDs([]string{"a1", "a1", " ", "a2"}) != 2 {
		t.Fatalf("超限附件未拦截或去重计数错误: %v", err)
	}
}
