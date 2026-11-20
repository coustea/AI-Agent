package window

import (
	"strings"
	"testing"

	"mentorly/internal/dialogue"
)

// TestCounterEstimate 验证估算器对不同字符类别的相对量级。
func TestCounterEstimate(t *testing.T) {
	c := Counter{}

	if got := c.Estimate(""); got != 0 {
		t.Errorf("空串应为 0，实际 %d", got)
	}

	// 纯 ASCII：约 4 字符 / token
	if got := c.Estimate("abcdefgh"); got != 2 {
		t.Errorf("8 个 ASCII 字符应估算为 2，实际 %d", got)
	}

	// 中文：约 1 字符 / token（"计算机系统" 是 5 个汉字）
	if got := c.Estimate("计算机系统"); got != 5 {
		t.Errorf("5 个汉字应估算为 5，实际 %d", got)
	}

	// 极短串至少为 1，避免全空白被算成 0
	if got := c.Estimate(" "); got < 1 {
		t.Errorf("空白串至少应为 1，实际 %d", got)
	}

	// 长文本应规模合理：不会夸张到每个字符一个 token
	long := strings.Repeat("a", 4000)
	if got := c.Estimate(long); got != 1000 {
		t.Errorf("4000 个 ASCII 应为 1000，实际 %d", got)
	}
}

// TestCountTurns 验证轮数统计只数 user 消息。
func TestCountTurns(t *testing.T) {
	msgs := []dialogue.Message{
		{Role: "user"}, {Role: "assistant"},
		{Role: "user"}, {Role: "assistant"},
		{Role: "user"},
	}
	if got := dialogue.CountTurns(msgs); got != 3 {
		t.Errorf("轮数应为 3，实际 %d", got)
	}
}

// TestStripCodeFence 验证去掉模型输出的外层代码围栏。
