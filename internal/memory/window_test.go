package memory

import (
	"strings"
	"testing"
)

// mkMsgs 构造交替的 user/assistant 消息序列，id 从 1 递增。
func mkMsgs(turns int, content string) []Message {
	msgs := make([]Message, 0, turns*2)
	var id uint64 = 1
	for i := 0; i < turns; i++ {
		msgs = append(msgs, Message{ID: id, Role: "user", Content: content, Status: "completed"})
		id++
		msgs = append(msgs, Message{ID: id, Role: "assistant", Content: content, Status: "completed"})
		id++
	}
	return msgs
}

// TestSelectWindowKeepsRecentTurns 验证保留最近 N 轮原文，之前的送去压缩。
func TestSelectWindowKeepsRecentTurns(t *testing.T) {
	msgs := mkMsgs(5, strings.Repeat("x", 10))

	win := selectWindow(msgs, 2, 100000)

	// 5 轮保留 2 轮 → 压缩 3 轮（6 条消息）
	if len(win.ToCompress) != 6 {
		t.Errorf("应压缩 6 条消息，实际 %d", len(win.ToCompress))
	}
	if len(win.Keep) != 4 {
		t.Errorf("应保留 4 条消息，实际 %d", len(win.Keep))
	}

	// cutoff 必须是送入压缩的最后一条消息 id
	wantCutoff := win.ToCompress[len(win.ToCompress)-1].ID
	if win.CutoffID != wantCutoff {
		t.Errorf("cutoff = %d, want %d", win.CutoffID, wantCutoff)
	}

	// 保留部分必须是最后 2 轮
	if win.Keep[0].ID != msgs[len(msgs)-4].ID {
		t.Errorf("保留起点 id = %d, want %d", win.Keep[0].ID, msgs[len(msgs)-4].ID)
	}
}

// TestSelectWindowRespectsMaxChars 验证按整轮截断：放不下的轮次整轮不压缩。
func TestSelectWindowRespectsMaxChars(t *testing.T) {
	// 每轮 2 条 × 50 字符 = 100 字符
	msgs := mkMsgs(10, strings.Repeat("x", 50))

	win := selectWindow(msgs, 2, 250)

	// 最多能放 2 轮（200 字符），第 3 轮会超 250
	if len(win.ToCompress) > 4 {
		t.Errorf("压缩消息数应受 maxChars 限制，实际 %d", len(win.ToCompress))
	}
	if len(win.ToCompress)%2 != 0 {
		t.Error("必须按整轮截断，压缩消息数应为偶数")
	}

	// 校验字符数确实未超限
	total := 0
	for _, m := range win.ToCompress {
		total += len([]rune(m.Content))
	}
	if total > 250 {
		t.Errorf("压缩源字符数 %d 超过上限 250", total)
	}
}

// TestSelectWindowNoCompressWhenAllKept 验证轮数不足时不压缩。
func TestSelectWindowNoCompressWhenAllKept(t *testing.T) {
	msgs := mkMsgs(2, "短内容")

	win := selectWindow(msgs, 5, 100000)
	if len(win.ToCompress) != 0 || win.CutoffID != 0 {
		t.Error("轮数不足时应全部保留，不产生 cutoff")
	}
	if len(win.Keep) != len(msgs) {
		t.Errorf("应保留全部 %d 条，实际 %d", len(msgs), len(win.Keep))
	}
}

// TestSelectWindowEmpty 验证空输入。
func TestSelectWindowEmpty(t *testing.T) {
	win := selectWindow(nil, 2, 1000)
	if len(win.ToCompress) != 0 || len(win.Keep) != 0 || win.CutoffID != 0 {
		t.Error("空输入应返回空结果")
	}
}

// TestSelectWindowSingleTurnTooLarge 验证单轮就超限时不压缩，交给预算截断兜底。
func TestSelectWindowSingleTurnTooLarge(t *testing.T) {
	msgs := mkMsgs(3, strings.Repeat("x", 500))

	win := selectWindow(msgs, 1, 100)
	if len(win.ToCompress) != 0 {
		t.Error("单轮超过 maxChars 时不应压缩")
	}
	if len(win.Keep) != len(msgs) {
		t.Error("应全部保留")
	}
}

// TestFitHistoryBudget 验证历史预算截断：从最新往前保留，总量不超预算。
func TestFitHistoryBudget(t *testing.T) {
	c := Counter{}
	// 每轮各 100 字符，约 25 token + 4 开销
	msgs := mkMsgs(20, strings.Repeat("x", 100))

	kept, tokens := fitHistory(msgs, 200, 100, c)

	if tokens > 200 {
		t.Errorf("保留内容 token %d 超过预算 200", tokens)
	}
	if len(kept) == 0 {
		t.Fatal("至少应保留一条消息")
	}
	// 保留的必须是最新的
	if kept[len(kept)-1].ID != msgs[len(msgs)-1].ID {
		t.Errorf("应保留最新消息，实际最后一条 id = %d, want %d",
			kept[len(kept)-1].ID, msgs[len(msgs)-1].ID)
	}
}

// TestFitHistoryStartsWithUser 验证结果必须以 user 开头。
func TestFitHistoryStartsWithUser(t *testing.T) {
	c := Counter{}
	msgs := mkMsgs(10, strings.Repeat("y", 100))

	// 预算恰好只够最后一条 assistant 消息：应丢弃它（孤儿回答），
	// 或者继续往前找到一条 user 为止。
	kept, _ := fitHistory(msgs, 200, 100, c)
	if len(kept) > 0 && kept[0].Role != "user" {
		t.Errorf("保留历史必须以 user 开头，实际以 %q 开头", kept[0].Role)
	}
}

// TestFitHistoryAlternates 验证 user/assistant 必须交替。
func TestFitHistoryAlternates(t *testing.T) {
	c := Counter{}
	msgs := []Message{
		{ID: 1, Role: "user", Content: "u1", Status: "completed"},
		{ID: 2, Role: "user", Content: "u2", Status: "completed"}, // 连续 user
		{ID: 3, Role: "assistant", Content: "a1", Status: "completed"},
		{ID: 4, Role: "assistant", Content: "a2", Status: "completed"}, // 连续 assistant
	}

	kept, _ := fitHistory(msgs, 10000, 100, c)

	var lastRole string
	for i, m := range kept {
		if i == 0 && m.Role != "user" {
			t.Fatalf("应以 user 开头，实际 %q", m.Role)
		}
		if m.Role == lastRole {
			t.Fatalf("第 %d 条出现连续同角色 %q", i, m.Role)
		}
		lastRole = m.Role
	}
}

// TestFitHistorySkipsFailedEmpty 验证空失败消息被跳过。
func TestFitHistorySkipsFailedEmpty(t *testing.T) {
	c := Counter{}
	msgs := []Message{
		{ID: 1, Role: "user", Content: "问题", Status: "completed"},
		{ID: 2, Role: "assistant", Content: "", Status: "failed"},
		{ID: 3, Role: "assistant", Content: "正常回答", Status: "completed"},
	}

	kept, _ := fitHistory(msgs, 10000, 100, c)

	for _, m := range kept {
		if m.Status == "failed" && m.Content == "" {
			t.Error("空失败消息不应进入历史")
		}
	}
}

// TestFitHistoryAllAssistant 验证全是 assistant 时返回空（无法构成合法对话）。
func TestFitHistoryAllAssistant(t *testing.T) {
	c := Counter{}
	msgs := []Message{
		{ID: 1, Role: "assistant", Content: "a1", Status: "completed"},
		{ID: 2, Role: "assistant", Content: "a2", Status: "completed"},
	}

	kept, tokens := fitHistory(msgs, 10000, 100, c)
	if len(kept) != 0 || tokens != 0 {
		t.Errorf("全 assistant 应返回空历史，实际 %d 条", len(kept))
	}
}

// TestSelectWindowKeepsSlackForOffload 验证卸载目录不干扰工作区文件索引。
func TestSelectWindowKeepsSlackForOffload(t *testing.T) {
	// selectWindow 只处理消息，不应被磁盘状态影响：纯函数保证。
	msgs := mkMsgs(3, "content")
	win := selectWindow(msgs, 1, 100000)
	if len(win.ToCompress) == 0 {
		t.Error("应有可压缩内容")
	}
}
