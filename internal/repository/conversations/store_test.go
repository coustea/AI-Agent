package conversations

import "testing"

func TestTruncateRunes(t *testing.T) {
	if got := truncateRunes("中文测试", 2); got != "中文" {
		t.Errorf("truncateRunes = %q", got)
	}
	if got := truncateRunes("ab", 5); got != "ab" {
		t.Errorf("短文本不应截断: %q", got)
	}
}
