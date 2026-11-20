package chat

import (
	"strings"
	"testing"
)

var testCounter = Counter{}

// TestFitRespectsBudget 验证历史裁剪遵守 token 预算。
func TestFitRespectsBudget(t *testing.T) {
	msgs := []Message{
		{ID: 1, Role: RoleUser, Content: strings.Repeat("问", 100)},
		{ID: 2, Role: RoleAssistant, Content: strings.Repeat("答", 100)},
		{ID: 3, Role: RoleUser, Content: strings.Repeat("问", 100)},
		{ID: 4, Role: RoleAssistant, Content: strings.Repeat("答", 100)},
	}

	kept, tokens := Fit(msgs, Budget{MaxMessages: 40, Tokens: 250}, testCounter)
	if tokens > 250 && len(kept) > 1 {
		t.Errorf("超出预算：tokens=%d, kept=%d", tokens, len(kept))
	}
}

// TestFitAlwaysKeepsOne 验证预算极小时仍保留至少一条。
func TestFitAlwaysKeepsOne(t *testing.T) {
	msgs := []Message{{ID: 1, Role: RoleUser, Content: "问题"}}
	kept, _ := Fit(msgs, Budget{Tokens: 1}, testCounter)
	if len(kept) != 1 {
		t.Errorf("应保留至少一条，实际 %d", len(kept))
	}
}

// TestFitStartsAndAlternates 验证结果以 user 开头且交替。
func TestFitStartsAndAlternates(t *testing.T) {
	msgs := []Message{
		{ID: 1, Role: RoleAssistant, Content: "孤儿回答"},
		{ID: 2, Role: RoleUser, Content: "问题"},
		{ID: 3, Role: RoleAssistant, Content: "回答"},
	}

	kept, _ := Fit(msgs, Budget{MaxMessages: 40, Tokens: 10000}, testCounter)
	if len(kept) == 0 {
		t.Fatal("不应为空")
	}
	if !kept[0].IsUser() {
		t.Errorf("应以 user 开头，实际 %q", kept[0].Role)
	}
	for i := 1; i < len(kept); i++ {
		if kept[i].Role == kept[i-1].Role {
			t.Errorf("第 %d 条与上一条角色相同", i)
		}
	}
}

// TestFitSkipsEmptyFailures 验证空的失败消息被跳过。
func TestFitSkipsEmptyFailures(t *testing.T) {
	msgs := []Message{
		{ID: 1, Role: RoleUser, Content: "问题"},
		{ID: 2, Role: RoleAssistant, Content: "", Status: StatusFailed},
		{ID: 3, Role: RoleUser, Content: "追问"},
	}

	kept, _ := Fit(msgs, Budget{MaxMessages: 40, Tokens: 10000}, testCounter)
	for _, m := range kept {
		if m.IsEmptyFailure() {
			t.Error("空的失败消息不应进入历史")
		}
	}
}

// TestSelectForCompressionKeepsRecentTurns 验证保留最近轮数。
func TestSelectForCompressionKeepsRecentTurns(t *testing.T) {
	var msgs []Message
	for i := 1; i <= 3; i++ {
		msgs = append(msgs,
			Message{ID: uint64(i*2 - 1), Role: RoleUser, Content: "问题"},
			Message{ID: uint64(i * 2), Role: RoleAssistant, Content: "回答"},
		)
	}

	res := SelectForCompression(msgs, 1, 10000)
	if len(res.ToCompress) != 4 {
		t.Errorf("应压缩前 2 轮共 4 条，实际 %d", len(res.ToCompress))
	}
	if len(res.Keep) != 2 {
		t.Errorf("应保留最后 1 轮共 2 条，实际 %d", len(res.Keep))
	}
	if res.CutoffID != 4 {
		t.Errorf("cutoff 应为 4，实际 %d", res.CutoffID)
	}
}

// TestSelectForCompressionAllKept 验证无可压缩内容时全部保留。
func TestSelectForCompressionAllKept(t *testing.T) {
	msgs := []Message{
		{ID: 1, Role: RoleUser, Content: "问题"},
		{ID: 2, Role: RoleAssistant, Content: "回答"},
	}

	res := SelectForCompression(msgs, 4, 10000)
	if len(res.ToCompress) != 0 || res.CutoffID != 0 {
		t.Errorf("不应压缩，实际 toCompress=%d cutoff=%d", len(res.ToCompress), res.CutoffID)
	}
}

// TestSelectForCompressionSkipsOversizeTurn 验证单轮超限时整轮不压缩。
func TestSelectForCompressionSkipsOversizeTurn(t *testing.T) {
	msgs := []Message{
		{ID: 1, Role: RoleUser, Content: strings.Repeat("x", 500)},
		{ID: 2, Role: RoleAssistant, Content: strings.Repeat("y", 500)},
		{ID: 3, Role: RoleUser, Content: "新问题"},
		{ID: 4, Role: RoleAssistant, Content: "新回答"},
	}

	res := SelectForCompression(msgs, 1, 100)
	if res.CutoffID != 0 {
		t.Errorf("单轮超限时不应压缩，实际 cutoff=%d", res.CutoffID)
	}
}
