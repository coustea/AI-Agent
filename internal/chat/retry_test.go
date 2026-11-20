package chat

import (
	"context"
	"errors"
	"fmt"
	"testing"
)

// TestIsTransientError 验证瞬时错误的判定。
//
// 这条判定直接决定「要不要重试模型调用」：
// 漏判会让偶发的网关断连变成整轮失败；误判会在参数错误上反复重试浪费时间。
func TestIsTransientError(t *testing.T) {
	transient := []error{
		errors.New("Post \"https://api.example.com\": EOF"),
		errors.New("connection reset by peer"),
		errors.New("read: broken pipe"),
		errors.New("request timeout"),
		errors.New("429 Too Many Requests"),
		errors.New("503 Service Unavailable"),
		errors.New("504 Gateway Timeout"),
		errors.New("server overloaded"),
	}
	for _, err := range transient {
		if !isTransientError(err) {
			t.Errorf("应判定为可重试: %v", err)
		}
	}

	permanent := []error{
		errors.New("invalid api key"),
		errors.New("model not found"),
		errors.New("invalid request body"),
		errors.New("content policy violation"),
	}
	for _, err := range permanent {
		if isTransientError(err) {
			t.Errorf("不应判定为可重试: %v", err)
		}
	}

	if isTransientError(nil) {
		t.Error("nil 不应判定为可重试")
	}
}

// TestIsTransientErrorIgnoresCase 验证大小写不敏感。
func TestIsTransientErrorIgnoresCase(t *testing.T) {
	cases := []string{
		"EOF", "eof", "Eof",
		"CONNECTION RESET BY PEER", "Connection Reset By Peer",
		"503 SERVICE UNAVAILABLE",
	}
	for _, msg := range cases {
		if !isTransientError(fmt.Errorf("%s", msg)) {
			t.Errorf("应判定为可重试（大小写不敏感）: %q", msg)
		}
	}
}

// TestIsTransientErrorContext 验证 ctx 错误不在瞬时判定里被误判。
// 取消与超时由调用方单独处理，不应靠关键字猜测。
func TestIsTransientErrorContext(t *testing.T) {
	// context.Canceled 的文本里含 "context canceled"，不应命中任何重试关键字
	if isTransientError(context.Canceled) {
		t.Error("context.Canceled 不应判定为可重试")
	}
}
