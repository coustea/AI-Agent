package llm

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestEncodeRequest_Semantics(t *testing.T) {
	req := Request{
		Messages: []Message{
			{Role: RoleSystem, Content: "sys"},
			{Role: RoleUser, Content: ""},
			{
				Role:             RoleAssistant,
				Content:          "",
				ReasoningContent: "内部思考，不得回传",
				ToolCalls:        []ToolCall{{ID: "call_1", Name: "bash", Arguments: `{"cmd":"ls"}`}},
			},
			{Role: RoleTool, ToolResult: &ToolResult{ToolCallID: "call_1", Name: "bash", Content: "file.txt"}},
		},
		Tools: []ToolDefinition{
			{Name: "bash", Description: "run bash", Parameters: json.RawMessage(`{}`)},
		},
	}

	data, err := encodeRequest("gpt-4o", req)
	if err != nil {
		t.Fatalf("unexpected encode error: %v", err)
	}

	if strings.Contains(string(data), "reasoning_content") {
		t.Fatalf("请求体绝对不能包含 reasoning_content")
	}

	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		t.Fatalf("payload 不是合法 JSON: %v", err)
	}

	if payload["model"] != "gpt-4o" {
		t.Errorf("model 错误: %v", payload["model"])
	}
	if payload["stream"] != true {
		t.Errorf("stream 必须为 true")
	}

	msgs := payload["messages"].([]any)
	if len(msgs) != 4 {
		t.Fatalf("期望 4 条消息，实际 %d", len(msgs))
	}

	// assistant 携带 tool_calls 且无文本时必须是 null
	assistant := msgs[2].(map[string]any)
	if assistant["content"] != nil {
		t.Errorf("assistant content 必须为 null，实际 %#v", assistant["content"])
	}

	// 单次请求覆盖模型
	reqWithOverride := req
	reqWithOverride.Model = "gpt-4o-mini"
	dataOverride, err := encodeRequest("gpt-4o", reqWithOverride)
	if err != nil {
		t.Fatalf("unexpected encode error: %v", err)
	}
	var payloadOverride map[string]any
	_ = json.Unmarshal(dataOverride, &payloadOverride)
	if payloadOverride["model"] != "gpt-4o-mini" {
		t.Errorf("动态覆盖模型失败: %v", payloadOverride["model"])
	}
}

func TestStream_ToolCallsAssembled(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		// 分片 1: 下发 tool_call 的 id 与 name
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"id\":\"call_abc\",\"function\":{\"name\":\"bash\",\"arguments\":\"\"}}]}}]}\n\n")
		// 分片 2: 下发 arguments 第 1 段
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"function\":{\"arguments\":\"{\\\"cmd\\\":\\\"\"}}]}}]}\n\n")
		// 分片 3: 下发 arguments 第 2 段
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"function\":{\"arguments\":\"ls -la\\\"}\"}}]}}]}\n\n")
		// 终结
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{},\"finish_reason\":\"tool_calls\"}]}\n\n")
		_, _ = io.WriteString(w, "data: [DONE]\n\n")
	}))
	defer server.Close()

	client := newTestClient(t, server.URL)
	stream, err := client.ChatStream(context.Background(), Request{
		Messages: []Message{{Role: RoleUser, Content: "run ls"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var terminal Chunk
	for c := range stream {
		if c.Terminal() {
			terminal = c
		}
	}

	if terminal.Finish != StopToolCalls {
		t.Errorf("终止原因期望 tool_calls，实际: %v", terminal.Finish)
	}
	if len(terminal.ToolCalls) != 1 {
		t.Fatalf("期望 1 个工具调用，实际 %d", len(terminal.ToolCalls))
	}
	tc := terminal.ToolCalls[0]
	if tc.ID != "call_abc" || tc.Name != "bash" || tc.Arguments != `{"cmd":"ls -la"}` {
		t.Errorf("工具调用跨分片还原错误: %+v", tc)
	}
}

func TestStream_TruncatedWithoutFinish(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"Hello half\"}}]}\n\n")
		// 中途直接关闭连接，没有 finish_reason 也未发送 [DONE]
	}))
	defer server.Close()

	client := newTestClient(t, server.URL)
	stream, err := client.ChatStream(context.Background(), Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var terminal Chunk
	for c := range stream {
		if c.Terminal() {
			terminal = c
		}
	}

	if terminal.Finish != StopTruncated {
		t.Errorf("期望终止原因为 truncated，实际: %v", terminal.Finish)
	}
	if !errors.Is(terminal.Err, ErrStreamTruncated) {
		t.Errorf("期望 ErrStreamTruncated，实际: %v", terminal.Err)
	}
}

func TestStream_CancelYieldsCanceled(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		flusher := w.(http.Flusher)
		for i := 0; i < 50; i++ {
			_, _ = io.WriteString(w, "data: {\"choices\":[{\"delta\":{\"content\":\"tick\"}}]}\n\n")
			flusher.Flush()
			time.Sleep(20 * time.Millisecond)
		}
	}))
	defer server.Close()

	client := newTestClient(t, server.URL)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stream, err := client.ChatStream(ctx, Request{
		Messages: []Message{{Role: RoleUser, Content: "hi"}},
	})
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	var terminal Chunk
	for c := range stream {
		if c.Delta != "" {
			cancel() // 收到首块后取消
		}
		if c.Terminal() {
			terminal = c
		}
	}

	if terminal.Finish != StopCanceled {
		t.Errorf("期望 canceled，实际 %v", terminal.Finish)
	}
	if !errors.Is(terminal.Err, context.Canceled) {
		t.Errorf("期望 context.Canceled，实际 %v", terminal.Err)
	}
}
