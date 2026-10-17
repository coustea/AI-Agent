package memory

import (
	"context"
	"testing"

	"my-agent/internal/protocol"
)

// 测试基本的追加、历史获取与清空
func TestSlidingWindowMemory_Basic(t *testing.T) {
	mem := NewSlidingWindowMemory(10)
	ctx := context.Background()

	_ = mem.Append(ctx, protocol.Message{Role: protocol.RoleUser, Content: "Hello"})
	_ = mem.Append(ctx, protocol.Message{Role: protocol.RoleAssistant, Content: "Hi there!"})

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
	if msgs[0].Role != protocol.RoleSystem || msgs[0].Content != "You are a coding assistant." {
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
	mem := NewSlidingWindowMemory(3) // 仅保留 3 条消息的极小窗口，测试回溯
	ctx := context.Background()

	// 轮次 1
	_ = mem.Append(ctx, protocol.Message{Role: protocol.RoleUser, Content: "Query 1"})
	_ = mem.Append(ctx, protocol.Message{Role: protocol.RoleAssistant, Content: "Answer 1"})

	// 轮次 2：包含工具调用与工具执行结果
	_ = mem.Append(ctx, protocol.Message{Role: protocol.RoleUser, Content: "Query 2"})
	_ = mem.Append(ctx, protocol.Message{
		Role: protocol.RoleAssistant,
		ToolCalls: []protocol.ToolCall{
			{ID: "call_1", Name: "calculator", Arguments: `{"expr":"1+1"}`},
		},
	})
	_ = mem.Append(ctx, protocol.Message{
		Role: protocol.RoleTool,
		ToolResult: &protocol.ToolResult{
			ToolCallID: "call_1",
			Name:       "calculator",
			Content:    "2",
		},
	})
	_ = mem.Append(ctx, protocol.Message{Role: protocol.RoleAssistant, Content: "Answer 2: result is 2"})

	// 轮次 3
	_ = mem.Append(ctx, protocol.Message{Role: protocol.RoleUser, Content: "Query 3"})
	_ = mem.Append(ctx, protocol.Message{Role: protocol.RoleAssistant, Content: "Answer 3"})

	// 总消息数 = 8 条。按 maxMessages=3，原切片理论起点为 index 5 (Answer 2)
	// 但如果 maxMessages 设为 4，理论切片起点为 index 4 (RoleTool)。
	// 验证：无论怎么切，绝不能以 RoleTool 或孤立的 ToolCalls 开头！
	for max := 2; max <= 6; max++ {
		testMem := NewSlidingWindowMemory(max)
		for _, m := range mem.History() {
			_ = testMem.Append(ctx, m)
		}

		ctxMsgs, err := testMem.BuildContext(ctx, "SysPrompt")
		if err != nil {
			t.Fatalf("BuildContext max=%d failed: %v", max, err)
		}

		// 第一条必须是 System
		if ctxMsgs[0].Role != protocol.RoleSystem {
			t.Errorf("max=%d: first message must be system", max)
		}

		// 第二条（即首条非系统消息）必须是 RoleUser，严禁是 RoleTool
		if len(ctxMsgs) > 1 {
			firstNonSys := ctxMsgs[1]
			if firstNonSys.Role != protocol.RoleUser {
				t.Errorf("max=%d: first non-system message MUST be RoleUser, but got %s", max, firstNonSys.Role)
			}
		}

		// 检查消息流中所有 RoleTool 前一条是否是发起了工具调用的 RoleAssistant
		for i := 1; i < len(ctxMsgs); i++ {
			if ctxMsgs[i].Role == protocol.RoleTool {
				prev := ctxMsgs[i-1]
				if prev.Role != protocol.RoleAssistant && prev.Role != protocol.RoleTool {
					t.Errorf("max=%d: RoleTool at %d preceded by illegal %s", max, i, prev.Role)
				}
			}
		}
	}
}
