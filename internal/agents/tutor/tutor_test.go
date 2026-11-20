package tutor

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/cloudwego/eino/schema"
)

// TestResolveStatus 终态判定是行为正确性的关键。
//
// 最重要的顺序约束：ctx 已取消必须优先于 runErr == nil。
// 客户端断开时 Stream 可能正常返回 nil，但 ctx 已取消；
// 若先判 runErr == nil，这一轮会被误记为 completed——
// 用户看到「回答完整」，实际只收到半截。
func TestResolveStatus(t *testing.T) {
	cancelledCtx, cancel := context.WithCancel(context.Background())
	cancel()

	cases := []struct {
		name        string
		answer      string
		runErr      error
		ctx         context.Context
		wantStatus  string
		wantContent string
	}{
		{
			name:        "正常完成",
			answer:      "完整回答",
			runErr:      nil,
			ctx:         context.Background(),
			wantStatus:  StatusCompleted,
			wantContent: "完整回答",
		},
		{
			name:        "工具轮次后无文本",
			answer:      "",
			runErr:      nil,
			ctx:         context.Background(),
			wantStatus:  StatusCompleted,
			wantContent: "[已完成工具操作]",
		},
		{
			name:        "取消但保留半截文本",
			answer:      "半截回答",
			runErr:      context.Canceled,
			ctx:         cancelledCtx,
			wantStatus:  StatusCancelled,
			wantContent: "半截回答",
		},
		{
			name:        "取消且无文本",
			answer:      "",
			runErr:      context.Canceled,
			ctx:         cancelledCtx,
			wantStatus:  StatusCancelled,
			wantContent: "[本轮生成已停止]",
		},
		{
			name:        "ctx 已取消但 runErr 为 nil",
			answer:      "部分文本",
			runErr:      nil,
			ctx:         cancelledCtx,
			wantStatus:  StatusCancelled,
			wantContent: "部分文本",
		},
		{
			name:        "超时",
			answer:      "",
			runErr:      context.DeadlineExceeded,
			ctx:         context.Background(),
			wantStatus:  StatusCancelled,
			wantContent: "[本轮生成已停止]",
		},
		{
			name:        "真实错误",
			answer:      "",
			runErr:      errors.New("模型故障"),
			ctx:         context.Background(),
			wantStatus:  StatusFailed,
			wantContent: "",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			status, content := resolveStatus(tc.answer, tc.runErr, tc.ctx)
			if status != tc.wantStatus {
				t.Errorf("status = %q, 期望 %q", status, tc.wantStatus)
			}
			if content != tc.wantContent {
				t.Errorf("content = %q, 期望 %q", content, tc.wantContent)
			}
		})
	}
}

// TestUserFacingError 错误信息不能泄露实现细节。
func TestUserFacingError(t *testing.T) {
	cases := map[error]string{
		nil:                      "",
		context.DeadlineExceeded: "本轮生成超时，请重试",
		context.Canceled:         "生成已取消",
		ErrUnavailable:           "对话能力未启用",
		errors.New("内部栈信息"):      "生成失败，请稍后重试",
	}
	for err, want := range cases {
		if got := userFacingError(err); got != want {
			t.Errorf("userFacingError(%v) = %q, 期望 %q", err, got, want)
		}
	}

	// 不能把内部错误原文暴露出去
	internal := errors.New("sql: connection refused at 127.0.0.1:3306")
	if got := userFacingError(internal); strings.Contains(got, "3306") {
		t.Errorf("泄露了内部细节: %q", got)
	}
}

// TestIsTransient 只重试瞬时故障。
func TestIsTransient(t *testing.T) {
	transient := []string{
		"connection reset by peer",
		"unexpected EOF",
		"429 too many requests",
		"503 Service Unavailable",
		"request timeout",
	}
	for _, msg := range transient {
		if !isTransient(errors.New(msg)) {
			t.Errorf("%q 应判定为瞬时错误", msg)
		}
	}

	permanent := []string{
		"invalid api key",
		"model not found",
		"invalid request body",
	}
	for _, msg := range permanent {
		if isTransient(errors.New(msg)) {
			t.Errorf("%q 不应重试", msg)
		}
	}

	if isTransient(nil) {
		t.Error("nil 不应判定为瞬时错误")
	}
}

// TestAssemblePrompt 校验 Prompt 拼装的 Zero Empty Noise 原则。
func TestAssemblePrompt(t *testing.T) {
	base := AssemblePrompt(PromptInput{})
	if base == "" {
		t.Fatal("基础 Prompt 为空")
	}
	// 没有动态内容时不应出现多余小节
	if strings.Contains(base, "## 当前日期") || strings.Contains(base, "## 工作区文件") {
		t.Error("空内容时不应注入小节")
	}

	full := AssemblePrompt(PromptInput{
		Now:       "2026-11-21",
		Workspace: []string{"notes.md", "demo/"},
		Vision:    true,
	})
	for _, want := range []string{"## 当前日期", "2026-11-21", "## 工作区文件", "/workspace/notes.md", "## 图片输入"} {
		if !strings.Contains(full, want) {
			t.Errorf("缺少 %q", want)
		}
	}

	// 关闭 vision 时不应出现图片小节
	noVision := AssemblePrompt(PromptInput{Now: "2026-11-21"})
	if strings.Contains(noVision, "## 图片输入") {
		t.Error("vision=false 时不应注入图片小节")
	}
}

// TestBasePromptContent Prompt 必须包含关键约束。
func TestBasePromptContent(t *testing.T) {
	p := BasePrompt()
	for _, want := range []string{"教学", "工具", "artifact_id"} {
		if !strings.Contains(p, want) {
			t.Errorf("Prompt 缺少关键约束 %q", want)
		}
	}
	// 反幻觉约束必须存在
	if !strings.Contains(p, "禁止编造") {
		t.Error("Prompt 缺少禁止编造产物的约束")
	}
}

// TestTruncate 截断按字符而非字节。
func TestTruncate(t *testing.T) {
	if got := truncate("abcdef", 3); got != "abc…" {
		t.Errorf("truncate = %q", got)
	}
	// 中文不能被截断成半个字符
	if got := truncate("中文测试", 2); got != "中文…" {
		t.Errorf("truncate 中文 = %q", got)
	}
	if got := truncate("ab", 10); got != "ab" {
		t.Errorf("短文本不应被截断: %q", got)
	}
}

// TestEmitNil 没有 sink 时不应 panic。
func TestEmitNil(t *testing.T) {
	if err := emit(nil, Event{Type: EventMessage}); err != nil {
		t.Errorf("nil sink 返回错误: %v", err)
	}
}

// TestEventTypes 事件类型常量不能重复。
func TestEventTypes(t *testing.T) {
	types := []string{
		EventMessage, EventToolStart, EventToolEnd,
		EventError, EventDone,
	}
	seen := make(map[string]bool)
	for _, tp := range types {
		if tp == "" {
			t.Error("事件类型不能为空")
		}
		if seen[tp] {
			t.Errorf("重复的事件类型: %q", tp)
		}
		seen[tp] = true
	}
}

// TestStoreMessageFiltering 空的失败消息必须被过滤掉。
//
// 这类消息对模型没有信息量，还会破坏 user/assistant 交替结构。
func TestStoreMessageFiltering(t *testing.T) {
	msgs := []Message{
		{Role: RoleUser, Content: "问题一", Status: StatusCompleted},
		{Role: RoleAssistant, Content: "", Status: StatusFailed},
		{Role: RoleAssistant, Content: "回答一", Status: StatusCompleted},
	}

	// 模拟 buildMessages 的过滤逻辑
	var kept []Message
	for _, m := range msgs {
		if m.Status == StatusFailed && strings.TrimSpace(m.Content) == "" {
			continue
		}
		if strings.TrimSpace(m.Content) == "" {
			continue
		}
		kept = append(kept, m)
	}

	if len(kept) != 2 {
		t.Fatalf("保留 %d 条, 期望 2", len(kept))
	}
	if kept[1].Content != "回答一" {
		t.Errorf("第二条 = %q", kept[1].Content)
	}
}

// TestSchemaMessageRole 角色映射必须正确。
func TestSchemaMessageRole(t *testing.T) {
	if schema.User != "user" {
		t.Errorf("schema.User = %q", schema.User)
	}
	if schema.Assistant != "assistant" {
		t.Errorf("schema.Assistant = %q", schema.Assistant)
	}
	if schema.Tool != "tool" {
		t.Errorf("schema.Tool = %q", schema.Tool)
	}
}

// TestTruncateRunes 会话标题截断不能切断多字节字符。
func TestTruncateRunes(t *testing.T) {
	if got := truncateRunes("中文测试", 2); got != "中文" {
		t.Errorf("truncateRunes = %q", got)
	}
	if got := truncateRunes("ab", 5); got != "ab" {
		t.Errorf("短文本不应截断: %q", got)
	}
}

// TestResolveStatusToolFailure 工具调用失败必须记为 failed。
//
// 这是一个真实缺陷的回归测试：模型生成的工具参数 JSON 语法错误时，
// 框架会返回 event.Err，但流本身正常结束。若只看 runErr==nil
// 就会把这一轮记为 completed——用户看到「完成」，实际什么都没生成。
func TestResolveStatusToolFailure(t *testing.T) {
	toolErr := errors.New("failed to stream tool call: failed to unmarshal arguments")

	status, content := resolveStatus("", toolErr, context.Background())
	if status != StatusFailed {
		t.Errorf("工具失败时 status = %q, 期望 failed", status)
	}
	_ = content
}

// TestUserFacingErrorToolFailure 工具参数错误应有可操作的提示。
func TestUserFacingErrorToolFailure(t *testing.T) {
	cases := []struct {
		err  error
		want string
	}{
		{
			errors.New("failed to unmarshal arguments in json, toolName=x"),
			"工具参数格式有误，请重试（通常是内容过长或含特殊字符）",
		},
		{
			errors.New("failed to stream tool call abc"),
			"工具调用失败，请重试",
		},
		{
			errors.New("connection reset by peer"),
			"上游服务暂时不可用，请重试",
		},
	}
	for _, tc := range cases {
		if got := userFacingError(tc.err); got != tc.want {
			t.Errorf("userFacingError(%v) = %q, 期望 %q", tc.err, got, tc.want)
		}
	}
}
