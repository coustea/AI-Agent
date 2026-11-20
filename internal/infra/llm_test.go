package infra

import (
	"strings"
	"testing"
)

// TestNormalizeBaseURL 验证 BaseURL 归一化与校验。
//
// 重点覆盖 HyperWeaver 配置里的坑：.env 填的是完整请求地址
// （带 /chat/completions），而 eino 会自行拼接该路径，
// 直接透传会变成 /v2/chat/completions/chat/completions 导致 404。
func TestNormalizeBaseURL(t *testing.T) {
	cases := []struct {
		name    string
		in      string
		want    string
		wantErr bool
	}{
		{"正常地址", "https://api.deepseek.com/v1", "https://api.deepseek.com/v1", false},
		{"尾部斜杠被去掉", "https://api.deepseek.com/v1/", "https://api.deepseek.com/v1", false},
		{"星火 v2", "https://maas-api.cn-huabei-1.xf-yun.com/v2", "https://maas-api.cn-huabei-1.xf-yun.com/v2", false},
		{"http 也允许", "http://127.0.0.1:18081/v1", "http://127.0.0.1:18081/v1", false},

		// 这些必须被拒绝
		{"带 chat/completions 后缀", "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions", "", true},
		{"空地址", "", "", true},
		{"缺 scheme", "api.deepseek.com/v1", "", true},
		{"非 http scheme", "ftp://example.com/v1", "", true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := normalizeBaseURL(tc.in)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("期望报错，实际得到 %q", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("不应报错: %v", err)
			}
			if got != tc.want {
				t.Errorf("normalizeBaseURL(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

// TestNormalizeBaseURLErrorMessage 验证错误信息给出可直接照做的修正值。
func TestNormalizeBaseURLErrorMessage(t *testing.T) {
	_, err := normalizeBaseURL("https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions")
	if err == nil {
		t.Fatal("应报错")
	}

	msg := err.Error()
	if !strings.Contains(msg, "chat/completions") {
		t.Errorf("错误信息应点明问题所在，实际: %s", msg)
	}
	// 必须提示正确写法，否则使用者只能靠猜
	if !strings.Contains(msg, "https://maas-api.cn-huabei-1.xf-yun.com/v2") {
		t.Errorf("错误信息应给出正确地址示例，实际: %s", msg)
	}
}

// TestNewCompleterNil 验证未配置模型时返回 nil（上层据此降级）。
func TestNewCompleterNil(t *testing.T) {
	if got := NewCompleter(nil); got != nil {
		t.Error("nil 模型应返回 nil Completer")
	}
}

// TestCompleterNilSafe 验证 nil Completer 调用不 panic。
func TestCompleterNilSafe(t *testing.T) {
	var c *Completer
	if _, err := c.Complete(nil, "s", "u"); err == nil {
		t.Error("nil Completer 应返回错误而非 panic")
	}
}
