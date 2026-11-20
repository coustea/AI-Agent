package window

import (
	"testing"

	"mentorly/internal/dialogue"
)

// mkMsgs 构造交替的 user/assistant 消息，id 从 1 递增。
func mkMsgs(pairs int, content string) []dialogue.Message {
	out := make([]dialogue.Message, 0, pairs*2)
	var id uint64 = 1
	for i := 0; i < pairs; i++ {
		out = append(out,
			dialogue.Message{ID: id, Role: dialogue.RoleUser, Content: content, Status: dialogue.StatusCompleted},
			dialogue.Message{ID: id + 1, Role: dialogue.RoleAssistant, Content: content, Status: dialogue.StatusCompleted},
		)
		id += 2
	}
	return out
}

// TestFitRespectsBudget 验证超出预算时只保留最新部分。
func TestFitRespectsBudget(t *testing.T) {
	msgs := mkMsgs(10, "内容")
	kept, tokens := Fit(msgs, Budget{MaxMessages: 40, Tokens: 40}, Counter{})

	if len(kept) == 0 {
		t.Fatal("预算内至少应保留一条")
	}
	if len(kept) >= len(msgs) {
		t.Errorf("应丢弃部分历史，实际保留 %d/%d", len(kept), len(msgs))
	}
	// 保留的必须是最新的一段。
	if kept[len(kept)-1].ID != msgs[len(msgs)-1].ID {
		t.Errorf("应保留最新消息，实际末条 id=%d", kept[len(kept)-1].ID)
	}
	if tokens == 0 {
		t.Error("token 估算不应为 0")
	}
}

// TestFitAlwaysKeepsOne 验证预算极小时仍至少保留一条，避免完全失去对话感。
func TestFitAlwaysKeepsOne(t *testing.T) {
	msgs := mkMsgs(5, "很长的一段内容用来消耗预算")
	kept, _ := Fit(msgs, Budget{MaxMessages: 40, Tokens: 1}, Counter{})
	if len(kept) == 0 {
		t.Fatal("预算极小时也应保留至少一条")
	}
}

// TestFitStartsAndAlternates 验证结果以 user 开头且 user/assistant 交替。
func TestFitStartsAndAlternates(t *testing.T) {
	msgs := mkMsgs(8, "内容")
	kept, _ := Fit(msgs, Budget{MaxMessages: 40, Tokens: 1000}, Counter{})

	if len(kept) == 0 {
		t.Fatal("不应为空")
	}
	if !kept[0].IsUser() {
		t.Errorf("第一条应为 user，实际 %s", kept[0].Role)
	}
	for i := 1; i < len(kept); i++ {
		if kept[i].Role == kept[i-1].Role {
			t.Errorf("第 %d 条与上一条角色连续重复: %s", i, kept[i].Role)
		}
	}
}

// TestFitSkipsEmptyFailures 验证空的失败消息被跳过。
func TestFitSkipsEmptyFailures(t *testing.T) {
	msgs := []dialogue.Message{
		{ID: 1, Role: dialogue.RoleUser, Content: "问题", Status: dialogue.StatusCompleted},
		{ID: 2, Role: dialogue.RoleAssistant, Content: "", Status: dialogue.StatusFailed},
		{ID: 3, Role: dialogue.RoleAssistant, Content: "回答", Status: dialogue.StatusCompleted},
		{ID: 4, Role: dialogue.RoleUser, Content: "再问", Status: dialogue.StatusCompleted},
		{ID: 5, Role: dialogue.RoleAssistant, Content: "再答", Status: dialogue.StatusCompleted},
	}
	kept, _ := Fit(msgs, Budget{MaxMessages: 40, Tokens: 1000}, Counter{})

	for _, m := range kept {
		if m.ID == 2 {
			t.Error("空的失败消息不应出现在历史中")
		}
	}
}

// TestFitBudgetTightStillHasUser 验证预算只够最后一条 assistant 时，会回补一条 user。
func TestFitBudgetTightStillHasUser(t *testing.T) {
	msgs := []dialogue.Message{
		{ID: 1, Role: dialogue.RoleUser, Content: "短问题", Status: dialogue.StatusCompleted},
		{ID: 2, Role: dialogue.RoleAssistant, Content: "这是一段很长的回答内容占据大部分预算", Status: dialogue.StatusCompleted},
	}
	kept, _ := Fit(msgs, Budget{MaxMessages: 40, Tokens: 15}, Counter{})

	if len(kept) == 0 {
		t.Fatal("不应为空")
	}
	if !kept[0].IsUser() {
		t.Error("回补后应以 user 开头")
	}
}

// TestSelectForCompressionKeepsRecentTurns 验证保留最近 N 轮。
func TestSelectForCompressionKeepsRecentTurns(t *testing.T) {
	msgs := mkMsgs(5, "内容")
	got := SelectForCompression(msgs, 2, 100000)

	if len(got.ToCompress) == 0 {
		t.Fatal("应compressed部分不为空")
	}
	if len(got.Keep) != 4 {
		t.Errorf("应保留最近 2 轮（4 条），实际 %d", len(got.Keep))
	}
	if got.CutoffID == 0 {
		t.Error("cutoff 不应为 0")
	}
	// cutoff 必须是压缩区间的最后一条。
	if got.CutoffID != got.ToCompress[len(got.ToCompress)-1].ID {
		t.Errorf("cutoff=%d 应等于压缩区间末条 id=%d", got.CutoffID, got.ToCompress[len(got.ToCompress)-1].ID)
	}
}

// TestSelectForCompressionAllKept 验证轮数不足时全部保留。
func TestSelectForCompressionAllKept(t *testing.T) {
	msgs := mkMsgs(2, "内容")
	got := SelectForCompression(msgs, 5, 100000)

	if len(got.ToCompress) != 0 {
		t.Errorf("轮数不足时不应压缩，实际 %d 条", len(got.ToCompress))
	}
	if len(got.Keep) != len(msgs) {
		t.Errorf("应全部保留 %d 条，实际 %d", len(msgs), len(got.Keep))
	}
}

// TestSelectForCompressionSkipsOversizeTurn 验证单轮超限时不压缩，交给预算截断。
func TestSelectForCompressionSkipsOversizeTurn(t *testing.T) {
	msgs := mkMsgs(5, "内容")
	got := SelectForCompression(msgs, 1, 1)

	if len(got.ToCompress) != 0 {
		t.Error("单轮即超限时不应选出压缩窗口")
	}
}
