package agent

import (
	"context"
	"errors"
	"testing"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/schema"
)

// fakeAgent 实现 adk.Agent 的最小接口，按脚本产出事件流。
//
// 用它替代真实模型：真实模型需要网络与 key，而 reset、最终回答提取、
// ctx 取消这些是纯编排逻辑，完全可以用脚本化事件精确覆盖。
type fakeAgent struct {
	// script 按顺序产出事件；每个元素要么是文本块，要么是工具调用块。
	script []fakeEvent
	// blockOnCtx 为 true 时，消费到第 blockAt 个事件后阻塞直到 ctx 取消，
	// 用于验证取消路径。
	blockOnCtx bool
	blockAt    int
}

type fakeEvent struct {
	text      string
	toolCalls []schema.ToolCall
	role      schema.RoleType
	toolName  string
	usage     *schema.TokenUsage
}

// Name 实现 adk.Agent。
func (f *fakeAgent) Name(_ context.Context) string { return "fake" }

// Description 实现 adk.Agent。
func (f *fakeAgent) Description(_ context.Context) string { return "fake agent" }

// Run 实现 adk.Agent，把脚本转成事件流。
func (f *fakeAgent) Run(ctx context.Context, _ *adk.AgentInput, _ ...adk.AgentRunOption) *adk.AsyncIterator[*adk.AgentEvent] {
	iter, gen := adk.NewAsyncIteratorPair[*adk.AgentEvent]()

	go func() {
		defer gen.Close()

		for i, ev := range f.script {
			if f.blockOnCtx && i == f.blockAt {
				<-ctx.Done()
				return
			}
			select {
			case <-ctx.Done():
				return
			default:
			}

			if ev.toolName != "" {
				gen.Send(&adk.AgentEvent{
					Output: &adk.AgentOutput{
						MessageOutput: &adk.MessageVariant{
							Role:     schema.Tool,
							ToolName: ev.toolName,
							Message:  &schema.Message{Role: schema.Tool, Content: ev.text},
						},
					},
				})
				continue
			}

			msg := &schema.Message{
				Role:    schema.Assistant,
				Content: ev.text,
			}
			if len(ev.toolCalls) > 0 {
				msg.ToolCalls = ev.toolCalls
			}
			if ev.usage != nil {
				msg.ResponseMeta = &schema.ResponseMeta{Usage: ev.usage}
			}

			gen.Send(&adk.AgentEvent{
				Output: &adk.AgentOutput{
					MessageOutput: &adk.MessageVariant{
						Role:    schema.Assistant,
						Message: msg,
					},
				},
			})
		}
	}()

	return iter
}

// 编译期断言。
var _ adk.Agent = (*fakeAgent)(nil)

// TestStreamPlainAnswer 验证无工具调用时的纯文本累积。
func TestStreamPlainAnswer(t *testing.T) {
	ag := &fakeAgent{script: []fakeEvent{
		{text: "你好，"},
		{text: "这是回答。"},
	}}
	runner := adk.NewRunner(context.Background(), adk.RunnerConfig{Agent: ag})

	var got []Chunk
	res, err := Stream(context.Background(), runner, nil, func(c Chunk) error {
		got = append(got, c)
		return nil
	})
	if err != nil {
		t.Fatalf("Stream: %v", err)
	}

	if res.Answer != "你好，这是回答。" {
		t.Errorf("最终回答不符: %q", res.Answer)
	}
	if res.Resets != 0 {
		t.Errorf("无工具调用不应 reset，实际 %d 次", res.Resets)
	}
	if len(got) != 2 {
		t.Errorf("应推 2 个文本块，实际 %d", len(got))
	}
}

// TestStreamResetOnToolCall 验证工具调用触发 reset，且过渡语不计入最终回答。
func TestStreamResetOnToolCall(t *testing.T) {
	ag := &fakeAgent{script: []fakeEvent{
		{text: "让我先看一下文件。"}, // 过渡语
		{toolCalls: []schema.ToolCall{
			{ID: "call-1", Type: "function", Function: schema.FunctionCall{Name: "read_file"}},
		}},
		{toolName: "read_file", text: "文件内容"},
		{text: "根据文件内容，答案是 42。"}, // 正式回答
	}}
	runner := adk.NewRunner(context.Background(), adk.RunnerConfig{Agent: ag})

	var (
		got      []Chunk
		sawReset bool
	)
	res, err := Stream(context.Background(), runner, nil, func(c Chunk) error {
		got = append(got, c)
		if c.Reset {
			sawReset = true
		}
		return nil
	})
	if err != nil {
		t.Fatalf("Stream: %v", err)
	}

	if !sawReset {
		t.Fatal("工具调用应触发 reset")
	}
	if res.Resets != 1 {
		t.Errorf("reset 次数应为 1，实际 %d", res.Resets)
	}
	// 关键断言：过渡语不可出现在最终回答里
	if res.Answer == "让我先看一下文件。" {
		t.Error("过渡语不应成为最终回答")
	}
	if res.Answer != "根据文件内容，答案是 42。" {
		t.Errorf("最终回答应只含 reset 之后的文本，实际 %q", res.Answer)
	}
	if len(res.ToolCalls) == 0 {
		t.Error("应记录工具调用")
	}

	// 客户端视角：应收到 reset 帧
	if !sawReset {
		t.Error("客户端应收到 reset 帧")
	}
}

// TestStreamUsage 验证真实用量被捕获。
func TestStreamUsage(t *testing.T) {
	usage := &schema.TokenUsage{PromptTokens: 100, CompletionTokens: 50, TotalTokens: 150}
	ag := &fakeAgent{script: []fakeEvent{{text: "回答", usage: usage}}}
	runner := adk.NewRunner(context.Background(), adk.RunnerConfig{Agent: ag})

	res, err := Stream(context.Background(), runner, nil, nil)
	if err != nil {
		t.Fatalf("Stream: %v", err)
	}
	if res.Usage == nil {
		t.Fatal("应捕获 Usage")
	}
	if res.Usage.TotalTokens != 150 {
		t.Errorf("TotalTokens = %d, want 150", res.Usage.TotalTokens)
	}
}

// TestStreamEmptyAnswer 验证「无工具调用且无文本」才返回 ErrEmptyAnswer。
func TestStreamEmptyAnswer(t *testing.T) {
	ag := &fakeAgent{script: []fakeEvent{{text: ""}}}
	runner := adk.NewRunner(context.Background(), adk.RunnerConfig{Agent: ag})

	res, err := Stream(context.Background(), runner, nil, nil)
	if !errors.Is(err, ErrEmptyAnswer) {
		t.Errorf("应返回 ErrEmptyAnswer，实际 %v", err)
	}
	if res.Answer != "" {
		t.Errorf("空回答不应有内容，实际 %q", res.Answer)
	}
}

// TestStreamToolOnlyIsSuccess 验证「调用了工具但最终无文本」不算失败。
// 这是真实模型常见的行为：完成文件操作后不再追加说明。
func TestStreamToolOnlyIsSuccess(t *testing.T) {
	ag := &fakeAgent{script: []fakeEvent{
		{toolCalls: []schema.ToolCall{
			{ID: "c1", Type: "function", Function: schema.FunctionCall{Name: "write_file"}},
		}},
		{toolName: "write_file", text: "写入成功"},
	}}
	runner := adk.NewRunner(context.Background(), adk.RunnerConfig{Agent: ag})

	res, err := Stream(context.Background(), runner, nil, nil)
	if err != nil {
		t.Fatalf("工具轮次不应报错，实际 %v", err)
	}
	if !res.HasToolOutput {
		t.Error("应标记产生了工具结果")
	}
	if res.Answer != "" {
		t.Errorf("没有文本输出时回答应为空，实际 %q", res.Answer)
	}
}

// TestStreamContextCancel 验证 ctx 取消时立即返回并保留已生成内容。
func TestStreamContextCancel(t *testing.T) {
	ag := &fakeAgent{
		script: []fakeEvent{
			{text: "正在生成"},
			{text: "后续内容"},
		},
		blockOnCtx: true,
		blockAt:    1,
	}
	runner := adk.NewRunner(context.Background(), adk.RunnerConfig{Agent: ag})

	ctx, cancel := context.WithCancel(context.Background())

	done := make(chan error, 1)
	var res *StreamResult

	go func() {
		var err error
		res, err = Stream(ctx, runner, nil, func(c Chunk) error {
			// 收到第一块后取消，模拟客户端断开
			if c.Text != "" {
				cancel()
			}
			return nil
		})
		done <- err
	}()

	err := <-done
	if err == nil {
		t.Fatal("ctx 取消时应返回错误")
	}
	if !errors.Is(err, context.Canceled) {
		t.Errorf("应返回 context.Canceled，实际 %v", err)
	}
	// 已生成的半截内容应被保留，供上层落库 cancelled
	if res == nil || res.Answer == "" {
		t.Error("取消时应保留已生成的部分内容")
	}
}

// TestStreamSinkError 验证 sink 报错时中止。
func TestStreamSinkError(t *testing.T) {
	ag := &fakeAgent{script: []fakeEvent{{text: "回答"}}}
	runner := adk.NewRunner(context.Background(), adk.RunnerConfig{Agent: ag})

	sinkErr := errors.New("连接已断")
	_, err := Stream(context.Background(), runner, nil, func(Chunk) error {
		return sinkErr
	})
	if !errors.Is(err, sinkErr) {
		t.Errorf("应向上传递 sink 错误，实际 %v", err)
	}
}

// TestToSchemaMessages 验证历史消息转换与空内容过滤。
func TestToSchemaMessages(t *testing.T) {
	msgs := []Message{
		{Role: "user", Content: "问题"},
		{Role: "assistant", Content: ""}, // 空内容应被过滤
		{Role: "assistant", Content: "回答"},
		{Role: "user", Content: "   "}, // 纯空白也应被过滤
	}

	out := ToSchemaMessages(msgs)
	if len(out) != 2 {
		t.Fatalf("应转换 2 条，实际 %d", len(out))
	}
	if out[0].Role != schema.User {
		t.Errorf("第一条角色应为 user，实际 %v", out[0].Role)
	}
	if out[1].Role != schema.Assistant {
		t.Errorf("第二条角色应为 assistant，实际 %v", out[1].Role)
	}
}
