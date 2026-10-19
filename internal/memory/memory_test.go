package memory

import (
	"context"
	"strings"
	"testing"

	"my-agent/pkg/llm"
)

// 测试基本的追加、历史获取与清空
func TestSlidingWindowMemory_Basic(t *testing.T) {
	mem := NewSlidingWindowMemory(10, 0)
	ctx := context.Background()

	_ = mem.Append(ctx, llm.Message{Role: llm.RoleUser, Content: "Hello"})
	_ = mem.Append(ctx, llm.Message{Role: llm.RoleAssistant, Content: "Hi there!"})

	history := mem.History()
	if len(history) != 2 {
		t.Fatalf("expected 2 messages in history, got %d", len(history))
	}
	if history[0].Content != "Hello" || history[1].Content != "Hi there!" {
		t.Errorf("unexpected history content: %+v", history)
	}

	// 验证 BuildContext 携带系统提示词
	msgs, err := mem.BuildContext(ctx, "You are a coding assistant.")
	if err != nil {
		t.Fatalf("BuildContext failed: %v", err)
	}
	if len(msgs) != 3 {
		t.Fatalf("expected 3 messages, got %d", len(msgs))
	}
	if msgs[0].Role != llm.RoleSystem || msgs[0].Content != "You are a coding assistant." {
		t.Errorf("expected system message first, got %+v", msgs[0])
	}

	// 清空测试
	mem.Clear()
	if len(mem.History()) != 0 {
		t.Errorf("expected history to be empty after clear, got %d", len(mem.History()))
	}
}

// 测试轮次原子性（Turn Atomicity）：绝不裁出孤立的 RoleTool
func TestSlidingWindowMemory_TurnAtomicity(t *testing.T) {
	mem := NewSlidingWindowMemory(3, 0) // 仅保留 3 条消息的极小窗口，测试回溯
	ctx := context.Background()

	// 轮次 1
	_ = mem.Append(ctx, llm.Message{Role: llm.RoleUser, Content: "Query 1"})
	_ = mem.Append(ctx, llm.Message{Role: llm.RoleAssistant, Content: "Answer 1"})

	// 轮次 2：包含工具调用与工具执行结果
	_ = mem.Append(ctx, llm.Message{Role: llm.RoleUser, Content: "Query 2"})
	_ = mem.Append(ctx, llm.Message{
		Role: llm.RoleAssistant,
		ToolCalls: []llm.ToolCall{
			{ID: "call_1", Name: "calculator", Arguments: `{"expr":"1+1"}`},
		},
	})
	_ = mem.Append(ctx, llm.Message{
		Role: llm.RoleTool,
		ToolResult: &llm.ToolResult{
			ToolCallID: "call_1",
			Name:       "calculator",
			Content:    "2",
		},
	})
	_ = mem.Append(ctx, llm.Message{Role: llm.RoleAssistant, Content: "Answer 2: result is 2"})

	// 轮次 3
	_ = mem.Append(ctx, llm.Message{Role: llm.RoleUser, Content: "Query 3"})
	_ = mem.Append(ctx, llm.Message{Role: llm.RoleAssistant, Content: "Answer 3"})

	// 总消息数 = 8 条。按 maxMessages=3，原切片理论起点为 index 5 (Answer 2)
	// 但如果 maxMessages 设为 4，理论切片起点为 index 4 (RoleTool)。
	// 验证：无论怎么切，绝不能以 RoleTool 或孤立的 ToolCalls 开头！
	for max := 2; max <= 6; max++ {
		testMem := NewSlidingWindowMemory(max, 0)
		for _, m := range mem.History() {
			_ = testMem.Append(ctx, m)
		}

		ctxMsgs, err := testMem.BuildContext(ctx, "SysPrompt")
		if err != nil {
			t.Fatalf("BuildContext max=%d failed: %v", max, err)
		}

		// 第一条必须是 System
		if ctxMsgs[0].Role != llm.RoleSystem {
			t.Errorf("max=%d: first message must be system", max)
		}

		// 第二条（即首条非系统消息）必须是 RoleUser，严禁是 RoleTool
		if len(ctxMsgs) > 1 {
			firstNonSys := ctxMsgs[1]
			if firstNonSys.Role != llm.RoleUser {
				t.Errorf("max=%d: first non-system message MUST be RoleUser, but got %s", max, firstNonSys.Role)
			}
		}

		// 检查消息流中所有 RoleTool 前一条是否是发起了工具调用的 RoleAssistant
		for i := 1; i < len(ctxMsgs); i++ {
			if ctxMsgs[i].Role == llm.RoleTool {
				prev := ctxMsgs[i-1]
				if prev.Role != llm.RoleAssistant && prev.Role != llm.RoleTool {
					t.Errorf("max=%d: RoleTool at %d preceded by illegal %s", max, i, prev.Role)
				}
			}
		}
	}
}

// 验收 D7：字符预算裁剪 + 工具调用配对完整性
func TestSlidingWindowMemory_ContextByteBudget(t *testing.T) {
	const budget = 500
	mem := NewSlidingWindowMemory(100, budget)

	// 20 条各 100 字符的 user/assistant 交替消息，总量远超预算
	for i := 0; i < 20; i++ {
		role := llm.RoleUser
		if i%2 == 1 {
			role = llm.RoleAssistant
		}
		_ = mem.Append(context.Background(), llm.Message{
			Role:    role,
			Content: strings.Repeat("x", 100),
		})
	}

	ctxMsgs, err := mem.BuildContext(context.Background(), "sys")
	if err != nil {
		t.Fatalf("BuildContext failed: %v", err)
	}

	total := 0
	for _, m := range ctxMsgs {
		if m.Role == llm.RoleSystem {
			continue
		}
		total += len(m.Content)
	}
	if total > budget {
		t.Errorf("context bytes %d exceed budget %d", total, budget)
	}
	if len(ctxMsgs) < 2 {
		t.Fatalf("expected some recent history retained, got %d", len(ctxMsgs))
	}
	// 必须保留最新一条
	if ctxMsgs[len(ctxMsgs)-1].Content != strings.Repeat("x", 100) {
		t.Errorf("latest message must be retained")
	}
}

// 预算裁剪不得拆散 assistant(tool_calls) 与其 tool 结果
func TestSlidingWindowMemory_ByteBudgetKeepsToolPairs(t *testing.T) {
	const budget = 200
	mem := NewSlidingWindowMemory(100, budget)
	ctx := context.Background()

	_ = mem.Append(ctx, llm.Message{Role: llm.RoleUser, Content: "run it"})
	_ = mem.Append(ctx, llm.Message{
		Role:    llm.RoleAssistant,
		Content: strings.Repeat("a", 120),
		ToolCalls: []llm.ToolCall{
			{ID: "tc1", Name: "bash", Arguments: `{"command":"ls"}`},
		},
	})
	_ = mem.Append(ctx, llm.Message{
		Role:       llm.RoleTool,
		ToolResult: &llm.ToolResult{ToolCallID: "tc1", Name: "bash", Content: strings.Repeat("b", 120)},
	})

	ctxMsgs, err := mem.BuildContext(ctx, "")
	if err != nil {
		t.Fatalf("BuildContext failed: %v", err)
	}
	if len(ctxMsgs) == 0 {
		t.Fatalf("expected tool pair retained")
	}
	// 首条不得是孤立 RoleTool
	if ctxMsgs[0].Role == llm.RoleTool {
		t.Fatalf("context must not start with orphan tool result")
	}
	// 若包含 tool 结果，其配对的 assistant(tool_calls) 必须在前面
	for i, m := range ctxMsgs {
		if m.Role != llm.RoleTool {
			continue
		}
		found := false
		for j := 0; j < i; j++ {
			if ctxMsgs[j].Role == llm.RoleAssistant && len(ctxMsgs[j].ToolCalls) > 0 {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("orphan tool result at index %d", i)
		}
	}
}

// TestSlidingWindowMemory_Compaction 验证超出双倍 maxMessages 阈值时触发平滑压实，释放过期历史并保全轮次原子性
func TestSlidingWindowMemory_Compaction(t *testing.T) {
	mem := NewSlidingWindowMemory(4, 0)
	ctx := context.Background()

	// 持续追加 10 条纯对话消息 (超过 4*2=8 阈值)
	for i := 1; i <= 5; i++ {
		_ = mem.Append(ctx, llm.Message{Role: llm.RoleUser, Content: "Q"})
		_ = mem.Append(ctx, llm.Message{Role: llm.RoleAssistant, Content: "A"})
	}

	history := mem.History()
	if len(history) > 6 {
		t.Fatalf("expected memory to be compacted below safety margin, got %d", len(history))
	}
	// 压实后的首条消息必须是 RoleUser，绝不留下断尾
	if history[0].Role != llm.RoleUser {
		t.Fatalf("compacted memory must start with RoleUser, got %s", history[0].Role)
	}
}
