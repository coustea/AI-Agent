package agent

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"my-agent/internal/config"
	"my-agent/internal/protocol"
)

// 本文件是唯一贯通全链路的集成测试：config → pkg/llm.Client → 真实 HTTP/SSE → Agent → 事件流。
// 它不依赖任何真实凭据，用一个最小 OpenAI 兼容网关充当上游。

// newFakeGateway 启动一个按给定 SSE 帧顺序回放的网关。
func newFakeGateway(t *testing.T, frames ...string) *httptest.Server {
	t.Helper()

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		flusher, _ := w.(http.Flusher)
		for _, frame := range frames {
			if _, err := io.WriteString(w, frame); err != nil {
				return
			}
			if flusher != nil {
				flusher.Flush()
			}
		}
	}))
	t.Cleanup(srv.Close)
	return srv
}

// newGatewayAgent 用测试网关装配一个就绪的 Agent。
func newGatewayAgent(t *testing.T, baseURL string) *CoreAgent {
	t.Helper()

	cfg := &config.Config{
		Provider:  config.ProviderDeepSeek,
		BaseURL:   baseURL,
		ModelName: config.ProviderSpec(config.ProviderDeepSeek).DefaultModel,
		APIKey:    "test-key",
	}
	ag, err := NewFromConfig(cfg,
		WithWorkDir(t.TempDir()),
		WithConfig(cfg, filepath.Join(t.TempDir(), "config.json")),
		WithMaxSteps(2),
	)
	if err != nil {
		t.Fatalf("装配 Agent 失败: %v", err)
	}
	return ag
}

// collectTurn 读取整轮事件直到通道关闭。
func collectTurn(t *testing.T, events <-chan protocol.Event) []protocol.Event {
	t.Helper()

	var out []protocol.Event
	timeout := time.After(10 * time.Second)
	for {
		select {
		case ev, ok := <-events:
			if !ok {
				return out
			}
			out = append(out, ev)
		case <-timeout:
			t.Fatalf("等待事件超时，已收到 %d 个事件", len(out))
		}
	}
}

// 完整链路：正常流 → EventDelta 拼接正确、EventDone 携带用量、无 EventError
func TestIntegration_NormalTurn(t *testing.T) {
	srv := newFakeGateway(t,
		"data: {\"choices\":[{\"delta\":{\"content\":\"你好\"}}]}\n\n",
		"data: {\"choices\":[{\"delta\":{\"content\":\"，世界\"}}]}\n\n",
		"data: {\"choices\":[],\"usage\":{\"prompt_tokens\":5,\"completion_tokens\":2,\"total_tokens\":7}}\n\n",
		"data: {\"choices\":[{\"delta\":{},\"finish_reason\":\"stop\"}]}\n\n",
		"data: [DONE]\n\n",
	)

	ag := newGatewayAgent(t, srv.URL)
	events, err := ag.Run(context.Background(), "打个招呼")
	if err != nil {
		t.Fatalf("Run 失败: %v", err)
	}

	var text strings.Builder
	var done *protocol.Event
	for i, ev := range collectTurn(t, events) {
		switch ev.Type {
		case protocol.EventDelta:
			text.WriteString(ev.Delta)
		case protocol.EventError:
			t.Fatalf("第 %d 个事件不应为错误: %s", i, ev.Error)
		case protocol.EventDone:
			doneEvent := ev
			done = &doneEvent
		}
	}

	if text.String() != "你好，世界" {
		t.Errorf("增量拼接错误: %q", text.String())
	}
	if done == nil {
		t.Fatalf("必须收到 EventDone")
	}
	if done.Usage == nil || done.Usage.TotalTokens != 7 {
		t.Errorf("EventDone 应携带 7 tokens，实际 %+v", done.Usage)
	}
}

// 回归 P0：上游中途断连必须以 EventError 收敛，绝不能发 EventDone 并把半截文本当成完成
func TestIntegration_TruncatedTurnFails(t *testing.T) {
	srv := newFakeGateway(t,
		"data: {\"choices\":[{\"delta\":{\"content\":\"半截回答\"}}]}\n\n",
		// 没有 finish_reason，也没有 [DONE]
	)

	ag := newGatewayAgent(t, srv.URL)
	events, err := ag.Run(context.Background(), "随便说说")
	if err != nil {
		t.Fatalf("Run 失败: %v", err)
	}

	var sawError, sawDone bool
	for _, ev := range collectTurn(t, events) {
		switch ev.Type {
		case protocol.EventError:
			sawError = true
			if !strings.Contains(ev.Error, "断开") && !strings.Contains(ev.Error, "llm:") {
				t.Errorf("错误文案应说明上游异常，实际 %q", ev.Error)
			}
		case protocol.EventDone:
			sawDone = true
		}
	}

	if !sawError {
		t.Errorf("截断的流必须产生 EventError")
	}
	if sawDone {
		t.Errorf("截断的流不得产生 EventDone")
	}
}
