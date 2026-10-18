package textutil

import (
	"strings"
	"testing"
	"unicode/utf8"
)

func TestTruncateUTF8(t *testing.T) {
	cases := []struct {
		name string
		in   string
		max  int
	}{
		{"ascii exact", "abcdef", 3},
		{"chinese", strings.Repeat("中文测试", 10), 7},
		{"emoji", strings.Repeat("🌊🌊🌊", 10), 10},
		{"mixed", "abc中文🌊def", 8},
		{"max zero", "abc", 0},
		{"shorter than max", "abc", 10},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			out := TruncateUTF8(tc.in, tc.max)
			if !utf8.ValidString(out) {
				t.Fatalf("result is not valid UTF-8: %q", out)
			}
			if tc.max > 0 && len(out) > tc.max {
				t.Fatalf("result exceeds max bytes: %d > %d", len(out), tc.max)
			}
			if !strings.HasPrefix(tc.in, out) {
				t.Fatalf("result must be a prefix of input")
			}
		})
	}
}
