package agent

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/tool"
	toolutils "github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
)

type capturedRequest struct {
	Thinking    map[string]any `json:"thinking"`
	Temperature float64        `json:"temperature"`
	MaxTokens   int            `json:"max_tokens"`
}

func newThinkingTestServer(t *testing.T, reply func(call int) map[string]any) (*httptest.Server, *[]capturedRequest, *sync.Mutex) {
	t.Helper()
	var (
		mu       sync.Mutex
		captured []capturedRequest
		calls    int
	)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req capturedRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Errorf("decode request body: %v", err)
		}
		mu.Lock()
		calls++
		n := calls
		captured = append(captured, req)
		mu.Unlock()

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(reply(n))
	}))
	t.Cleanup(srv.Close)
	return srv, &captured, &mu
}

func chatCompletionResp(content string, toolCalls ...map[string]any) map[string]any {
	msg := map[string]any{"role": "assistant", "content": content}
	finish := "stop"
	if len(toolCalls) > 0 {
		msg["tool_calls"] = toolCalls
		finish = "tool_calls"
	}
	return map[string]any{
		"id":      "chatcmpl-test",
		"object":  "chat.completion",
		"created": 1,
		"model":   "spark-x2.6",
		"choices": []map[string]any{{"index": 0, "message": msg, "finish_reason": finish}},
	}
}

func runAgentOnce(t *testing.T, a adk.Agent, prompt string) {
	t.Helper()
	runner := adk.NewRunner(t.Context(), adk.RunnerConfig{Agent: a, EnableStreaming: false})
	iter := runner.Run(t.Context(), []*schema.Message{schema.UserMessage(prompt)})
	for {
		ev, ok := iter.Next()
		if !ok {
			return
		}
		if ev.Err != nil {
			t.Fatalf("agent run error: %v", ev.Err)
		}
	}
}

func TestThinkingFirstCallOnlyPerUserTurn(t *testing.T) {
	srv, captured, mu := newThinkingTestServer(t, func(call int) map[string]any {
		switch call {
		case 1, 4:
			return chatCompletionResp("", map[string]any{
				"id": "call-1", "type": "function",
				"function": map[string]any{"name": "echo", "arguments": `{}`},
			})
		case 2:
			return chatCompletionResp("", map[string]any{
				"id": "call-2", "type": "function",
				"function": map[string]any{"name": "echo", "arguments": `{}`},
			})
		default:
			return chatCompletionResp("完成")
		}
	})

	maxTokens := 131072
	cm, err := openai.NewChatModel(t.Context(), &openai.ChatModelConfig{
		MaxTokens:   &maxTokens,
		BaseURL:     srv.URL,
		APIKey:      "test-key",
		Model:       "spark-x2.6",
		ExtraFields: map[string]any{"temperature": 0.7},
	})
	if err != nil {
		t.Fatal(err)
	}

	echoTool, err := toolutils.InferTool("echo", "echo tool", func(context.Context, struct{}) (string, error) {
		return "ok", nil
	})
	if err != nil {
		t.Fatal(err)
	}

	a, err := adk.NewChatModelAgent(t.Context(), &adk.ChatModelAgentConfig{
		Name:        "test-thinking",
		Model:       cm,
		ToolsConfig: adk.ToolsConfig{ToolsNodeConfig: compose.ToolsNodeConfig{Tools: []tool.BaseTool{echoTool}}},
		Handlers: []adk.ChatModelAgentMiddleware{
			newTokenBudget(1000000, 131072, "tutor"),
			newThinking(thinkingFirstCallOnly, "spark", map[string]any{"temperature": 0.7}),
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	runAgentOnce(t, a, "第一条用户消息")
	runAgentOnce(t, a, "第二条用户消息")

	mu.Lock()
	got := append([]capturedRequest(nil), (*captured)...)
	mu.Unlock()

	wantTypes := []string{"enabled", "disabled", "disabled", "enabled", "disabled"}
	if len(got) != len(wantTypes) {
		t.Fatalf("captured %d calls, want %d: %+v", len(got), len(wantTypes), got)
	}
	for i, want := range wantTypes {
		if got[i].Thinking["type"] != want {
			t.Errorf("call #%d thinking.type = %v, want %q", i+1, got[i].Thinking["type"], want)
		}
		if got[i].Temperature != 0.7 {
			t.Errorf("call #%d temperature = %v, want 0.7", i+1, got[i].Temperature)
		}
		if got[i].MaxTokens != 131072 {
			t.Errorf("call #%d max_tokens = %d, want 131072", i+1, got[i].MaxTokens)
		}
	}
}

func TestThinkingStaticModesAndNonSparkPassthrough(t *testing.T) {
	cases := []struct {
		name     string
		provider string
		mode     string
		wantType any
	}{
		{"always", "spark", thinkingAlways, "enabled"},
		{"disabled", "spark", thinkingDisabled, "disabled"},
		{"off", "spark", thinkingOff, nil},
		{"non-spark", "openai", thinkingFirstCallOnly, nil},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			srv, captured, mu := newThinkingTestServer(t, func(int) map[string]any {
				return chatCompletionResp("ok")
			})
			cm, err := openai.NewChatModel(t.Context(), &openai.ChatModelConfig{
				BaseURL: srv.URL, APIKey: "test-key", Model: "test-model",
			})
			if err != nil {
				t.Fatal(err)
			}
			a, err := adk.NewChatModelAgent(t.Context(), &adk.ChatModelAgentConfig{
				Name:     "test-mode-" + tc.name,
				Model:    cm,
				Handlers: []adk.ChatModelAgentMiddleware{newThinking(tc.mode, tc.provider, nil)},
			})
			if err != nil {
				t.Fatal(err)
			}
			runAgentOnce(t, a, "hi")

			mu.Lock()
			defer mu.Unlock()
			if len(*captured) != 1 {
				t.Fatalf("calls = %d, want 1", len(*captured))
			}
			got := (*captured)[0].Thinking
			if tc.wantType == nil && got != nil {
				t.Fatalf("unexpected thinking field: %+v", got)
			}
			if tc.wantType != nil && (got == nil || got["type"] != tc.wantType) {
				t.Fatalf("thinking = %+v, want type=%v", got, tc.wantType)
			}
		})
	}
}

func TestThinkingWithoutRunStateDisablesThinking(t *testing.T) {
	srv, captured, mu := newThinkingTestServer(t, func(int) map[string]any { return chatCompletionResp("ok") })
	cm, err := openai.NewChatModel(t.Context(), &openai.ChatModelConfig{BaseURL: srv.URL, APIKey: "test-key", Model: "test-model"})
	if err != nil {
		t.Fatal(err)
	}
	wrapped, err := newThinking("", "spark", nil).WrapModel(t.Context(), cm, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := wrapped.Generate(t.Context(), []*schema.Message{schema.UserMessage("hi")}); err != nil {
		t.Fatal(err)
	}
	mu.Lock()
	defer mu.Unlock()
	if len(*captured) != 1 || (*captured)[0].Thinking["type"] != "disabled" {
		t.Fatalf("缺少运行状态时应关闭思考: %+v", *captured)
	}
}
