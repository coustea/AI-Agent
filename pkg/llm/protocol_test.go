package llm

import (
	"encoding/json"
	"errors"
	"strings"
	"testing"
)

// decodePayload 把编码结果解成通用 map，便于断言字段的存在性与 null 语义。
func decodePayload(t *testing.T, data []byte) map[string]any {
	t.Helper()

	var out map[string]any
	if err := json.Unmarshal(data, &out); err != nil {
		t.Fatalf("请求体不是合法 JSON: %v", err)
	}
	return out
}

// assistant 携带 tool_calls 且无文本时必须发 content: null；
// tool 消息要摊平；reasoning_content 绝不能出现在请求体里。
func TestEncodeRequest_MessageSemantics(t *testing.T) {
	req := Request{
		Messages: []Message{
			{Role: RoleSystem, Content: "sys"},
			{Role: RoleUser, Content: ""},
			{
				Role:             RoleAssistant,
				Content:          "",
				ReasoningContent: "内部思考链，不能回传",
				ToolCalls:        []ToolCall{{ID: "call_1", Name: "bash", Arguments: `{"cmd":"ls"}`}},
			},
			{Role: RoleTool, ToolResult: &ToolResult{ToolCallID: "call_1", Name: "bash", Content: "out"}},
		},
	}

	data, err := encodeRequest("deepseek-flash", req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if strings.Contains(string(data), "reasoning_content") {
		t.Fatalf("请求体不得包含 reasoning_content: %s", data)
	}

	payload := decodePayload(t, data)
	if payload["stream"] != true {
		t.Errorf("stream 必须为 true")
	}
	opts, ok := payload["stream_options"].(map[string]any)
	if !ok || opts["include_usage"] != true {
		t.Errorf("必须声明 stream_options.include_usage，否则拿不到用量")
	}

	msgs := payload["messages"].([]any)
	if len(msgs) != 4 {
		t.Fatalf("期望 4 条消息，实际 %d", len(msgs))
	}

	// user 的空文本必须是 ""（而不是 null）
	user := msgs[1].(map[string]any)
	if content, exists := user["content"]; !exists || content != "" {
		t.Errorf("user 空文本应为 \"\"，实际 %#v", content)
	}

	// assistant 无文本 + 有 tool_calls 必须是 null
	assistant := msgs[2].(map[string]any)
	content, exists := assistant["content"]
	if !exists || content != nil {
		t.Errorf("assistant 带 tool_calls 时 content 必须为 null，实际 %#v", content)
	}
	calls := assistant["tool_calls"].([]any)
	call := calls[0].(map[string]any)
	if call["id"] != "call_1" || call["type"] != "function" {
		t.Errorf("tool_calls 编码错误: %#v", call)
	}

	// tool 消息摊平为 content + tool_call_id + name
	tool := msgs[3].(map[string]any)
	if tool["role"] != "tool" || tool["content"] != "out" || tool["tool_call_id"] != "call_1" || tool["name"] != "bash" {
		t.Errorf("tool 消息摊平错误: %#v", tool)
	}
}

// 模型名由 Client 在构造时绑定，若 Request 显式指定则优先使用 Request.Model
func TestEncodeRequest_ModelFromClient(t *testing.T) {
	data, err := encodeRequest("client-model", Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got := decodePayload(t, data)["model"]; got != "client-model" {
		t.Errorf("期望 client-model，实际 %v", got)
	}

	// 动态覆盖模型
	overrideData, err := encodeRequest("client-model", Request{
		Model:    "request-model-override",
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got := decodePayload(t, overrideData)["model"]; got != "request-model-override" {
		t.Errorf("期望 request-model-override，实际 %v", got)
	}
}

func TestEncodeRequest_EmptyMessages(t *testing.T) {
	if _, err := encodeRequest("", Request{}); !errors.Is(err, ErrEmptyMessages) {
		t.Errorf("空消息应返回 ErrEmptyMessages，实际 %v", err)
	}
}

// 纯 usage chunk（choices 为空数组）不能被当作解析失败
func TestDecodeData_UsageOnlyChunk(t *testing.T) {
	d, err := decodeData([]byte(`{"choices":[],"usage":{"prompt_tokens":3,"completion_tokens":4,"total_tokens":7}}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if d.usage == nil || d.usage.TotalTokens != 7 {
		t.Fatalf("应解析出用量，实际 %+v", d.usage)
	}
	if d.delta != "" || d.hasFinish {
		t.Errorf("纯 usage chunk 不应产生增量或终止信号")
	}
}

// finish_reason 为 null 表示流未结束，不能被当成结束
func TestDecodeData_FinishReasonSemantics(t *testing.T) {
	d, err := decodeData([]byte(`{"choices":[{"delta":{"content":"x"},"finish_reason":null}]}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if d.hasFinish {
		t.Errorf("finish_reason 为 null 时不应产生终止信号")
	}

	d, _ = decodeData([]byte(`{"choices":[{"delta":{},"finish_reason":"length"}]}`))
	if !d.hasFinish || d.finish != StopLength {
		t.Errorf("期望 StopLength，实际 %s", d.finish)
	}
}

func TestStopReason_Mapping(t *testing.T) {
	cases := map[string]StopReason{
		"stop":           StopEnd,
		"tool_calls":     StopToolCalls,
		"function_call":  StopToolCalls,
		"length":         StopLength,
		"max_tokens":     StopLength,
		"content_filter": StopContentFilter,
		"":               StopEnd,
		"未知原因":           StopEnd,
	}
	for raw, want := range cases {
		if got := stopReason(raw); got != want {
			t.Errorf("stopReason(%q) 期望 %s，实际 %s", raw, want, got)
		}
	}
}

// 厂商错误信封必须被识别，而不是当作空 chunk 跳过
func TestDecodeData_ErrorEnvelope(t *testing.T) {
	d, err := decodeData([]byte(`{"error":{"message":"invalid model","type":"invalid_request_error"}}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if d.apiErr != "invalid model" {
		t.Errorf("应提取 error.message，实际 %q", d.apiErr)
	}
}

func TestDecodeData_InvalidJSON(t *testing.T) {
	if _, err := decodeData([]byte(`not json`)); !errors.Is(err, ErrProtocolViolation) {
		t.Errorf("期望 ErrProtocolViolation，实际 %v", err)
	}
}

// 错误体解析兼容 {"error":{...}} 与 {"message":...} 两种信封
func TestErrorMessage(t *testing.T) {
	if got := errorMessage(`{"error":{"message":"boom"}}`); got != "boom" {
		t.Errorf("期望 boom，实际 %q", got)
	}
	if got := errorMessage(`{"message":"boom2"}`); got != "boom2" {
		t.Errorf("期望 boom2，实际 %q", got)
	}
	if got := errorMessage("plain text"); got != "" {
		t.Errorf("非 JSON 应返回空串，实际 %q", got)
	}
}

// clip 按字符截断，不能切碎多字节字符
func TestClip_UTF8Safe(t *testing.T) {
	got := clip(strings.Repeat("中", 10), 3)
	if got != "中中中…" {
		t.Errorf("期望按字符截断，实际 %q", got)
	}
}

// 思考链别名兼容：当上游返回 reasoning 而非 reasoning_content 时正常解析
func TestDecodeData_ReasoningFallback(t *testing.T) {
	d, err := decodeData([]byte(`{"choices":[{"delta":{"content":"ans","reasoning":"think"}}]}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if d.delta != "ans" || d.reasoning != "think" {
		t.Errorf("期望 delta=ans, reasoning=think，实际 delta=%q, reasoning=%q", d.delta, d.reasoning)
	}
}
