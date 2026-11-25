package agent

import (
	"context"
	"errors"
	"reflect"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"
	"go.uber.org/zap/zaptest/observer"

	logutil "mentorly/internal/utils/log"
)

// ---------- Principal & Model ----------

func TestPrincipalRoundTripAndMissing(t *testing.T) {
	p := &runPrincipal{UserID: "u1", ConversationID: "c1", Workspace: "/tmp/ws"}
	ctx := withPrincipal(context.Background(), p)
	got, ok := principalFrom(ctx)
	if !ok || got.UserID != "u1" || got.ConversationID != "c1" {
		t.Fatalf("身份读取失败: %+v ok=%v", got, ok)
	}
	if _, ok := principalFrom(context.Background()); ok {
		t.Error("空 context 不应有身份")
	}
	if _, ok := principalFrom(withPrincipal(context.Background(), &runPrincipal{ConversationID: "c1"})); ok {
		t.Error("空 UserID 不应视为有效身份")
	}
	if _, ok := principalFrom(withPrincipal(context.Background(), nil)); ok {
		t.Error("nil 身份不应有效")
	}
	if _, err := mustPrincipal(context.Background()); !errors.Is(err, errNoPrincipal) {
		t.Errorf("错误 = %v, 期望 errNoPrincipal", err)
	}
	if _, err := mustPrincipal(ctx); err != nil {
		t.Errorf("意外错误: %v", err)
	}
}

func TestNormalizeBaseURL(t *testing.T) {
	okCases := map[string]string{
		"https://api.example.com/v1":   "https://api.example.com/v1",
		"https://api.example.com/v1/":  "https://api.example.com/v1",
		"http://127.0.0.1:8080":        "http://127.0.0.1:8080",
		" https://api.example.com/v1 ": "https://api.example.com/v1",
	}
	for in, want := range okCases {
		got, err := normalizeBaseURL(in)
		if err != nil || got != want {
			t.Errorf("normalizeBaseURL(%q) = (%q, %v), want %q", in, got, err, want)
		}
	}
	for _, bad := range []string{"", "api.example.com/v1", "ftp://api.example.com", "https://api.example.com/v1/chat/completions"} {
		if _, err := normalizeBaseURL(bad); err == nil {
			t.Errorf("normalizeBaseURL(%q) 应报错", bad)
		}
	}
}

// ---------- Status, Errors & Events ----------

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
		{"正常完成", "完整回答", nil, context.Background(), StatusCompleted, "完整回答"},
		{"工具轮次后无最终结果", "", errEmptyAgentOutput, context.Background(), StatusFailed, "Agent 未返回最终结果，请检查工作区文件或重试"},
		{"取消但保留半截文本", "半截回答", context.Canceled, cancelledCtx, StatusCancelled, "半截回答"},
		{"取消且无文本", "", context.Canceled, cancelledCtx, StatusCancelled, "[本轮生成已停止]"},
		{"ctx 已取消但 runErr 为 nil", "部分文本", nil, cancelledCtx, StatusCancelled, "部分文本"},
		{"超时", "", context.DeadlineExceeded, context.Background(), StatusCancelled, "[本轮生成已停止]"},
		{"真实错误", "", errors.New("模型故障"), context.Background(), StatusFailed, "生成失败，请稍后重试"},
		{"工具参数错误", "", errors.New("failed to stream tool call: failed to unmarshal arguments"), context.Background(), StatusFailed, "工具参数格式有误，请重试（通常是内容过长或含特殊字符）"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			status, content := resolveStatus(tc.answer, tc.runErr, tc.ctx)
			if status != tc.wantStatus || content != tc.wantContent {
				t.Errorf("got=(%q, %q), want=(%q, %q)", status, content, tc.wantStatus, tc.wantContent)
			}
		})
	}
}

func TestUserFacingErrorAndTransient(t *testing.T) {
	cases := map[error]string{
		nil:                                                                "",
		context.DeadlineExceeded:                                           "本轮生成超时，请重试",
		context.Canceled:                                                   "生成已取消",
		ErrUnavailable:                                                  "对话能力未启用",
		errOutputTruncated:                                              "模型单次思考或输出超过长度上限，请缩小单次需求范围或重试",
		errors.New("内部栈信息"):                                            "生成失败，请稍后重试",
		errors.New("failed to unmarshal arguments in json, toolName=x"):    "工具参数格式有误，请重试（通常是内容过长或含特殊字符）",
		errors.New("failed to stream tool call abc"):                       "工具调用失败，请重试",
		errors.New("connection reset by peer"):                             "上游服务暂时不可用，请重试",
	}
	for err, want := range cases {
		if got := userFacingError(err); got != want {
			t.Errorf("userFacingError(%v) = %q, want %q", err, got, want)
		}
	}
	if got := userFacingError(errors.New("sql: connection refused at 127.0.0.1:3306")); strings.Contains(got, "3306") {
		t.Errorf("泄露内部细节: %q", got)
	}
	for _, msg := range []string{"connection reset by peer", "unexpected EOF", "429 too many requests", "503 Service Unavailable", "request timeout"} {
		if !isTransient(errors.New(msg)) {
			t.Errorf("%q 应判定为瞬时错误", msg)
		}
	}
	for _, msg := range []string{"invalid api key", "model not found", "invalid request body"} {
		if isTransient(errors.New(msg)) {
			t.Errorf("%q 不应重试", msg)
		}
	}
	if isTransient(nil) {
		t.Error("nil 不应判定为瞬时错误")
	}
}

func TestTruncateEmitAndEventTypes(t *testing.T) {
	if got := truncate("abcdef", 3); got != "abc…" {
		t.Errorf("truncate = %q", got)
	}
	if got := truncate("中文测试", 2); got != "中文…" {
		t.Errorf("truncate 中文 = %q", got)
	}
	if got := truncate("ab", 10); got != "ab" {
		t.Errorf("短文本不应截断: %q", got)
	}
	if err := emit(nil, Event{Type: EventMessage}); err != nil {
		t.Errorf("nil sink 返回错误: %v", err)
	}
	types := []string{EventMessage, EventToolStart, EventToolEnd, EventError, EventDone}
	seen := make(map[string]bool)
	for _, tp := range types {
		if tp == "" || seen[tp] {
			t.Fatalf("非法或重复事件类型: %q", tp)
		}
		seen[tp] = true
	}
	if schema.User != "user" || schema.Assistant != "assistant" || schema.Tool != "tool" {
		t.Fatal("schema 角色映射异常")
	}
}

// ---------- Stream, Callbacks & Retry ----------

func TestStreamPreservesNativeMessageAndLogs(t *testing.T) {
	for _, disconnect := range []bool{false, true} {
		msg := &schema.Message{Role: schema.Assistant, Content: "正文", ReasoningContent: "推理", Extra: map[string]any{"source": "model"}, ResponseMeta: &schema.ResponseMeta{Usage: &schema.TokenUsage{TotalTokens: 9}}}
		var buf strings.Builder
		res := &Result{}
		writeErr := errors.New("disconnected")
		err := consumeStream(t.Context(), schema.StreamReaderFromArray([]*schema.Message{msg}), &buf, func(Event) error {
			if disconnect {
				return writeErr
			}
			return nil
		}, res, map[string]time.Time{}, func() error { return nil }, nil)
		if disconnect && !errors.Is(err, writeErr) || !disconnect && err != nil {
			t.Fatalf("stream error: %v", err)
		}
		if res.Message == nil || res.Message.ReasoningContent != "推理" || res.Message.Extra["source"] != "model" || res.Message.ResponseMeta.Usage.TotalTokens != 9 {
			t.Fatalf("native fields lost: %+v", res.Message)
		}
	}

	// 验证流式日志合并、Token/推理统计（仅长度不含原文）、断连标记与工具参数脱敏
	core, logs := observer.New(zap.InfoLevel)
	ctx := logutil.WithContext(t.Context(), zap.New(core))
	var buf strings.Builder
	res := &Result{}
	chunks := []*schema.Message{
		{Role: schema.Assistant, Content: "真实", ReasoningContent: "不要记录推理"},
		{Role: schema.Assistant, Content: "回答", ResponseMeta: &schema.ResponseMeta{
			FinishReason: "stop",
			Usage: &schema.TokenUsage{
				PromptTokens:            100,
				CompletionTokens:        40,
				TotalTokens:             140,
				CompletionTokensDetails: schema.CompletionTokensDetails{ReasoningTokens: 25},
			},
		}},
	}
	if err := consumeStream(ctx, schema.StreamReaderFromArray(chunks), &buf, nil, res, map[string]time.Time{}, func() error { return nil }, &runMetrics{}); err != nil {
		t.Fatal(err)
	}
	if logs.Len() != 2 || logs.All()[0].Message != "[模型响应统计]" || logs.All()[1].Message != "[Agent 输出]" || logs.All()[1].ContextMap()["内容"] != "真实回答" {
		t.Fatalf("unexpected logs: %+v", logs.All())
	}
	stat := logs.All()[0].ContextMap()
	if stat["finish_reason"] != "stop" || stat["reasoning_chars"] != int64(6) || stat["prompt_tokens"] != int64(100) || stat["completion_tokens"] != int64(40) || stat["reasoning_tokens"] != int64(25) {
		t.Fatalf("unexpected usage stats: %+v", stat)
	}
	for _, entry := range logs.All() {
		for _, v := range entry.ContextMap() {
			if s, ok := v.(string); ok && strings.Contains(s, "不要记录推理") {
				t.Fatalf("推理原文不应写入日志: %+v", entry)
			}
		}
	}

	core2, logs2 := observer.New(zap.InfoLevel)
	ctx2 := logutil.WithContext(t.Context(), zap.New(core2))
	disconnect := errors.New("disconnected")
	var buf2 strings.Builder
	if err := consumeStream(ctx2, schema.StreamReaderFromArray([]*schema.Message{{Content: "已生成部分"}}), &buf2,
		func(Event) error { return disconnect }, &Result{}, map[string]time.Time{}, func() error { return nil }, nil); !errors.Is(err, disconnect) {
		t.Fatalf("error: %v", err)
	}
	if logs2.Len() != 1 || logs2.All()[0].Message != "[Agent 输出中断]" {
		t.Fatalf("logs: %+v", logs2.All())
	}

	core3, logs3 := observer.New(zap.InfoLevel)
	logAssistant(logutil.WithContext(t.Context(), zap.New(core3)), schema.AssistantMessage("", []schema.ToolCall{{ID: "hidden-call-id", Function: schema.FunctionCall{Name: "read_attachment", Arguments: `{"id":"attachment-1","offset":10}`}}}), false, 0)
	if logs3.Len() != 1 || logs3.All()[0].Message != "[Agent 工具调用：read_attachment]" || len(logs3.All()[0].Context) != 1 {
		t.Fatalf("tool log unexpected: %+v", logs3.All())
	}
}

func TestEventWriteFailureStopsConsumption(t *testing.T) {
	writeErr := errors.New("SSE 写入失败")
	reader, writer := schema.Pipe[*schema.Message](1)
	writer.Send(&schema.Message{Content: "部分回答"}, nil)
	writer.Close()
	var answer strings.Builder
	err := consumeStream(t.Context(), reader, &answer, func(Event) error { return writeErr }, &Result{}, map[string]time.Time{}, func() error { return nil }, nil)
	if !errors.Is(err, writeErr) || answer.String() != "部分回答" {
		t.Fatalf("流式写入错误未中止消费: answer=%q err=%v", answer.String(), err)
	}

	result := &Result{}
	err = startTools(func(Event) error { return writeErr }, result, map[string]time.Time{}, []schema.ToolCall{{ID: "call-1", Function: schema.FunctionCall{Name: "read_file"}}})
	if !errors.Is(err, writeErr) {
		t.Fatalf("工具事件写入错误未传播: %v", err)
	}
	if status, _ := resolveStatus(answer.String(), err, t.Context()); status == StatusCompleted {
		t.Fatal("SSE 写入失败不能判为成功")
	}
}

type retryTestModel struct {
	stream func(context.Context, []*schema.Message) (*schema.StreamReader[*schema.Message], error)
}

func (m *retryTestModel) WithTools([]*schema.ToolInfo) (model.ToolCallingChatModel, error) {
	return m, nil
}
func (m *retryTestModel) Generate(context.Context, []*schema.Message, ...model.Option) (*schema.Message, error) {
	return nil, errors.New("unexpected Generate")
}
func (m *retryTestModel) Stream(ctx context.Context, input []*schema.Message, _ ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	return m.stream(ctx, input)
}

func TestEmptyResponseRecoveryThroughRunner(t *testing.T) {
	for _, remainsEmpty := range []bool{false, true} {
		t.Run(map[bool]string{false: "recovered", true: "exhausted"}[remainsEmpty], func(t *testing.T) {
			ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
			defer cancel()
			var calls, executions atomic.Int32
			var previous []*schema.Message
			var sameInput atomic.Bool
			probe, err := utils.InferTool("probe", "probe environment", func(context.Context, struct{}) (string, error) {
				executions.Add(1)
				return "available", nil
			})
			if err != nil {
				t.Fatal(err)
			}
			m := &retryTestModel{stream: func(_ context.Context, input []*schema.Message) (*schema.StreamReader[*schema.Message], error) {
				n := calls.Add(1)
				var chunks []*schema.Message
				switch n {
				case 1:
					chunks = []*schema.Message{schema.AssistantMessage("", []schema.ToolCall{{ID: "probe-1", Type: "function", Function: schema.FunctionCall{Name: "probe", Arguments: "{}"}}})}
				case 2:
					previous = append([]*schema.Message(nil), input...)
					chunks = []*schema.Message{{Role: schema.Assistant, ReasoningContent: "internal", ResponseMeta: &schema.ResponseMeta{FinishReason: "stop"}}}
				default:
					sameInput.Store(reflect.DeepEqual(previous, input))
					if !remainsEmpty {
						chunks = []*schema.Message{schema.AssistantMessage("完成", nil)}
					}
				}
				return schema.StreamReaderFromArray(chunks), nil
			}}
			native, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
				Name: "test", Model: m,
				ToolsConfig:      adk.ToolsConfig{ToolsNodeConfig: compose.ToolsNodeConfig{Tools: []tool.BaseTool{probe}}},
				ModelRetryConfig: &adk.ModelRetryConfig{MaxRetries: 2, ShouldRetry: newRetryDecision("openai", nil), BackoffFunc: func(context.Context, int) time.Duration { return 0 }},
			})
			if err != nil {
				t.Fatal(err)
			}
			a := &Agent{agent: native, log: zap.NewNop()}
			var events []Event
			result := a.Run(ctx, &RunContext{Messages: []*schema.Message{schema.UserMessage("生成课件")}}, func(e Event) error { events = append(events, e); return nil })
			if calls.Load() != 3 || executions.Load() != 1 || !sameInput.Load() {
				t.Fatalf("calls=%d tools=%d same input=%v", calls.Load(), executions.Load(), sameInput.Load())
			}
			if len(result.Transcript) != 2 || len(result.Transcript[0].ToolCalls) != 1 || result.Transcript[1].ToolCallID != result.Transcript[0].ToolCalls[0].ID {
				t.Fatalf("unpaired transcript: %+v", result.Transcript)
			}
			want := StatusCompleted
			if remainsEmpty {
				want = StatusFailed
			}
			if result.Status != want {
				t.Fatalf("status=%s content=%s", result.Status, result.Message.Content)
			}
			var errorEvents int
			for _, e := range events {
				if e.Type == EventError {
					errorEvents++
				}
			}
			if !remainsEmpty && (errorEvents != 0 || result.Message.Content != "完成") {
				t.Fatalf("recovery result=%+v errors=%d", result, errorEvents)
			}
			if remainsEmpty && (errorEvents != 1 || result.Message.Content != userFacingError(errEmptyAgentOutput)) {
				t.Fatalf("failure result=%+v errors=%d", result, errorEvents)
			}
		})
	}
}

func TestRetryDecisionEmptyAndCancellation(t *testing.T) {
	sparkRetry := newRetryDecision("spark", map[string]any{"temperature": 0.7})
	openaiRetry := newRetryDecision("openai", nil)

	for _, msg := range []*schema.Message{nil, {Content: "  "}, {ReasoningContent: "thinking"}} {
		rc := &adk.RetryContext{OutputMessage: msg, RetryAttempt: 1}
		if !sparkRetry(t.Context(), rc).Retry {
			t.Fatal("empty response not retried")
		}
		rc.RetryAttempt = 2
		d := sparkRetry(t.Context(), rc)
		if d.Retry || !errors.Is(d.RewriteError, errEmptyAgentOutput) {
			t.Fatalf("unexpected exhausted decision: %+v", d)
		}
	}
	for _, msg := range []*schema.Message{{Content: "ok"}, {ToolCalls: []schema.ToolCall{{ID: "x"}}}, {AssistantGenMultiContent: []schema.MessageOutputPart{{}}}} {
		if sparkRetry(t.Context(), &adk.RetryContext{OutputMessage: msg, RetryAttempt: 1}).Retry {
			t.Fatal("valid output retried")
		}
	}
	ctx, cancel := context.WithCancel(t.Context())
	cancel()
	if d := sparkRetry(ctx, &adk.RetryContext{RetryAttempt: 1}); d.Retry || !errors.Is(d.RewriteError, context.Canceled) {
		t.Fatalf("cancellation ignored: %+v", d)
	}
	for _, err := range []error{context.Canceled, context.DeadlineExceeded} {
		if sparkRetry(t.Context(), &adk.RetryContext{Err: err, RetryAttempt: 1}).Retry {
			t.Fatal("cancelled call retried")
		}
	}
	if d := sparkRetry(t.Context(), &adk.RetryContext{Err: errors.New("status code: 429, request frequency limit exceeded"), RetryAttempt: 1}); !d.Retry || d.Backoff < 3*time.Second {
		t.Fatalf("429 应退避重试: %+v", d)
	}

	// finish_reason=length：spark 有推理时首次降级关闭思考重试 1 次；二次、无推理或非 spark 立即失败不盲目重跑。
	lengthWithReasoning := &schema.Message{
		ReasoningContent: "很长的思考",
		ResponseMeta: &schema.ResponseMeta{
			FinishReason: "length",
			Usage:        &schema.TokenUsage{CompletionTokens: 16384, CompletionTokensDetails: schema.CompletionTokensDetails{ReasoningTokens: 16384}},
		},
	}
	d1 := sparkRetry(t.Context(), &adk.RetryContext{OutputMessage: lengthWithReasoning, RetryAttempt: 1})
	if !d1.Retry || len(d1.AdditionalOptions) != 1 {
		t.Fatalf("spark 推理吃满 length 应降级重试 1 次: %+v", d1)
	}
	d2 := sparkRetry(t.Context(), &adk.RetryContext{OutputMessage: lengthWithReasoning, RetryAttempt: 2})
	if d2.Retry || !errors.Is(d2.RewriteError, errOutputTruncated) {
		t.Fatalf("length 二次截断不应再重试: %+v", d2)
	}
	lengthNoReasoning := &schema.Message{ResponseMeta: &schema.ResponseMeta{FinishReason: "length"}}
	if d := sparkRetry(t.Context(), &adk.RetryContext{OutputMessage: lengthNoReasoning, RetryAttempt: 1}); d.Retry || !errors.Is(d.RewriteError, errOutputTruncated) {
		t.Fatalf("无推理 length 截断不应盲目重试: %+v", d)
	}
	if d := openaiRetry(t.Context(), &adk.RetryContext{OutputMessage: lengthWithReasoning, RetryAttempt: 1}); d.Retry || !errors.Is(d.RewriteError, errOutputTruncated) {
		t.Fatalf("非 spark length 截断不应盲目重试: %+v", d)
	}

	// 剩余 deadline 不足时禁止发起重试。
	shortFallbackCtx, cancelFallback := context.WithTimeout(t.Context(), 5*time.Second)
	defer cancelFallback()
	if d := sparkRetry(shortFallbackCtx, &adk.RetryContext{OutputMessage: lengthWithReasoning, RetryAttempt: 1}); d.Retry || !errors.Is(d.RewriteError, errOutputTruncated) {
		t.Fatalf("剩余时间不足不应降级重试: %+v", d)
	}
	tightCtx, tightCancel := context.WithTimeout(t.Context(), 1*time.Second)
	defer tightCancel()
	if d := sparkRetry(tightCtx, &adk.RetryContext{Err: errors.New("status code: 429"), RetryAttempt: 1}); d.Retry {
		t.Fatalf("剩余时间不足不应 429 重试: %+v", d)
	}
}

func TestUnknownToolsHandlerRecoversThroughRunner(t *testing.T) {
	ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
	defer cancel()

	var sawFeedback atomic.Bool
	dummy, err := utils.InferTool("noop", "noop tool", func(context.Context, struct{}) (string, error) {
		return "ok", nil
	})
	if err != nil {
		t.Fatal(err)
	}
	m := &retryTestModel{stream: func(_ context.Context, input []*schema.Message) (*schema.StreamReader[*schema.Message], error) {
		for _, msg := range input {
			if msg.Role == schema.Tool && msg.ToolCallID == "bad-tool-1" && strings.Contains(msg.Content, "不存在") {
				sawFeedback.Store(true)
				return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("已改用正确方式完成", nil)}), nil
			}
		}
		return schema.StreamReaderFromArray([]*schema.Message{
			schema.AssistantMessage("", []schema.ToolCall{{ID: "bad-tool-1", Type: "function", Function: schema.FunctionCall{Name: "hallucinated_tool", Arguments: `{}`}}}),
		}), nil
	}}

	native, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
		Name:  "test",
		Model: m,
		ToolsConfig: adk.ToolsConfig{
			ToolsNodeConfig: compose.ToolsNodeConfig{
				Tools: []tool.BaseTool{dummy},
				UnknownToolsHandler: func(_ context.Context, name, _ string) (string, error) {
					return "工具 " + name + " 不存在。", nil
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	a := &Agent{agent: native, log: zap.NewNop()}
	res := a.Run(ctx, &RunContext{Messages: []*schema.Message{schema.UserMessage("测试未知工具")}}, nil)
	if res.Status != StatusCompleted || !sawFeedback.Load() || res.Message.Content != "已改用正确方式完成" {
		t.Fatalf("未知工具未恢复: status=%s saw=%v content=%q err=%v", res.Status, sawFeedback.Load(), res.Message.Content, res.runErr)
	}
}

func TestRejectedStreamDiscardAndSSEFailure(t *testing.T) {
	for _, disconnect := range []bool{false, true} {
		reader, writer := schema.Pipe[*schema.Message](3)
		writer.Send(&schema.Message{Content: "rejected"}, nil)
		writer.Send(nil, &adk.WillRetryError{ErrStr: "retrying"})
		writer.Close()
		var buf strings.Builder
		res := &Result{}
		writeErr := errors.New("SSE disconnected")
		reset := func() error {
			buf.Reset()
			res.Message = nil
			if disconnect {
				return writeErr
			}
			return nil
		}
		err := consumeStream(t.Context(), reader, &buf, nil, res, map[string]time.Time{}, reset, nil)
		if disconnect && !errors.Is(err, writeErr) || !disconnect && err != nil {
			t.Fatalf("error=%v", err)
		}
		if res.Message != nil || buf.Len() != 0 || len(res.Transcript) != 0 {
			t.Fatalf("rejected output retained: %+v", res)
		}
	}
}

// ---------- Context Compaction ----------

type summaryTestModel struct {
	genCalls atomic.Int32
}

func (m *summaryTestModel) WithTools([]*schema.ToolInfo) (model.ToolCallingChatModel, error) {
	return m, nil
}
func (m *summaryTestModel) Generate(_ context.Context, _ []*schema.Message, _ ...model.Option) (*schema.Message, error) {
	m.genCalls.Add(1)
	return schema.AssistantMessage("<analysis>ok</analysis><summary>已总结历史\n<all_user_messages>\n- u\n</all_user_messages></summary>", nil), nil
}
func (m *summaryTestModel) Stream(_ context.Context, _ []*schema.Message, _ ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("继续讲解", nil)}), nil
}

func TestSummarizationCapturesCompactionAndPreservesSkills(t *testing.T) {
	ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
	defer cancel()

	ws := t.TempDir()
	m := &summaryTestModel{}
	a, err := New(ctx, AgentDeps{
		Model: m,
		Config: Config{
			SkillsDir:              "skills",
			WorkspaceDir:           ws,
			SummaryTriggerTokens:   60000,
			SummaryTriggerMessages: 2,
		},
		Log: zap.NewNop(),
	})
	if err != nil {
		t.Fatal(err)
	}

	history := []*schema.Message{
		schema.UserMessage("做一份课件"),
		schema.AssistantMessage("", []schema.ToolCall{{ID: "sk-1", Type: "function", Function: schema.FunctionCall{Name: "skill", Arguments: `{"skill":"pptx"}`}}}),
		schema.ToolMessage("PPTX 制作规范正文", "sk-1", schema.WithToolName("skill")),
		schema.AssistantMessage("好的，先定大纲", nil),
		schema.UserMessage("继续生成第 2 页"),
	}

	res := a.Run(ctx, &RunContext{
		principal: &runPrincipal{UserID: "u1", ConversationID: "c1", Workspace: ws},
		Messages:  history,
	}, nil)
	if res.Status != StatusCompleted || m.genCalls.Load() != 1 {
		t.Fatalf("压缩未按预期完成: status=%s genCalls=%d", res.Status, m.genCalls.Load())
	}
	if res.Compaction == nil || len(res.Compaction.Messages) < 2 || res.Compaction.FoldedTranscriptCount != 0 {
		t.Fatalf("未捕获压缩检查点或缺失 PreserveSkills: %+v", res.Compaction)
	}
	var sawSkill, sawSummary bool
	for _, msg := range res.Compaction.Messages {
		if msg.Role == schema.System {
			t.Fatal("持久化检查点不应包含 System 消息")
		}
		if strings.Contains(msg.Content, "PPTX 制作规范正文") {
			sawSkill = true
		}
		if strings.Contains(msg.Content, "已总结历史") {
			sawSummary = true
		}
	}
	if !sawSkill || !sawSummary {
		t.Fatalf("检查点缺少技能或摘要内容: %+v", res.Compaction.Messages)
	}
}
