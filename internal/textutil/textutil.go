// Package textutil 提供跨包共享的文本处理小工具。
package textutil

import (
	"strings"
	"unicode/utf8"
)

// TruncateUTF8 按字节上限截断字符串，并保证结果是合法 UTF-8：
// 截断点回退到最近的字符边界，再用 ToValidUTF8 兜底。
func TruncateUTF8(s string, maxBytes int) string {
	if maxBytes <= 0 || len(s) <= maxBytes {
		return s
	}
	cut := maxBytes
	for cut > 0 && !utf8.RuneStart(s[cut]) {
		cut--
	}
	return strings.ToValidUTF8(s[:cut], "")
}
