package memory

import (
	"context"
	"strings"
	"sync"

	"my-agent/internal/protocol"
)

// SlidingWindowMemory 基于滑动窗口并严格保证轮次原子性（Turn Atomicity）的记忆实现。
// 裁剪历史时，保证 User -> Assistant(ToolCalls) -> Tool(ToolResult) 永远同生共死，绝不产生孤立的 RoleTool。
// 同时按字符预算（近似 token）从最新向前累计，防止长任务撑爆模型上下文。
type SlidingWindowMemory struct {
	mu              sync.RWMutex
	messages        []protocol.Message
	maxMessages     int
	maxContextBytes int
}

// NewSlidingWindowMemory 创建滑动窗口记忆实例。
// maxMessages 限制保留条数，maxContextBytes 限制保留上下文的字符预算（≤0 表示不限制）。
func NewSlidingWindowMemory(maxMessages, maxContextBytes int) *SlidingWindowMemory {
	if maxMessages <= 0 {
		maxMessages = 40
	}
	return &SlidingWindowMemory{
		messages:        make([]protocol.Message, 0),
		maxMessages:     maxMessages,
		maxContextBytes: maxContextBytes,
	}
}

// Append 追加一条消息到记忆中。
func (m *SlidingWindowMemory) Append(ctx context.Context, msg protocol.Message) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.messages = append(m.messages, msg)
	return nil
}

// History 返回当前全部消息的副本。
func (m *SlidingWindowMemory) History() []protocol.Message {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return append([]protocol.Message(nil), m.messages...)
}

// Clear 清空记忆。
func (m *SlidingWindowMemory) Clear() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.messages = make([]protocol.Message, 0)
}

// BuildContext 构建准备发往模型的上下文序列，自动注入 systemPrompt 并按轮次原子性进行安全裁剪。
func (m *SlidingWindowMemory) BuildContext(ctx context.Context, systemPrompt string) ([]protocol.Message, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	raw := m.messages
	total := len(raw)

	systemPrompt = strings.TrimSpace(systemPrompt)

	if total == 0 {
		if systemPrompt != "" {
			return []protocol.Message{{Role: protocol.RoleSystem, Content: systemPrompt}}, nil
		}
		return []protocol.Message{}, nil
	}

	startIdx := 0
	if total > m.maxMessages {
		startIdx = total - m.maxMessages
	}

	// 轮次原子性回溯：
	// 确保切片的起点永远不是孤立的 RoleTool 或孤立的 RoleAssistant(ToolCalls)
	for startIdx > 0 {
		// 1. 如果起点落在 RoleTool，向前寻找发出该调用的 RoleAssistant
		if raw[startIdx].Role == protocol.RoleTool {
			startIdx--
			continue
		}
		// 2. 如果落在发起了 ToolCalls 的 RoleAssistant 上，进一步向前包含发起提问的 RoleUser
		if raw[startIdx].Role == protocol.RoleAssistant && len(raw[startIdx].ToolCalls) > 0 {
			if startIdx > 0 && raw[startIdx-1].Role == protocol.RoleUser {
				startIdx--
			}
			break
		}
		// 3. 如果已经对齐到完整的 RoleUser，对齐完毕
		if raw[startIdx].Role == protocol.RoleUser {
			break
		}
		startIdx--
	}

	// 字符预算裁剪：以轮次（User 起点）为最小裁剪单位整轮丢弃，
	// 直到上下文 ≤ 预算；最后一轮始终保留（否则无法继续对话）。
	// 字符近似 token ≈ 4:1，不引入 tokenizer 依赖。
	if m.maxContextBytes > 0 {
		for startIdx < total {
			used := 0
			for i := startIdx; i < total; i++ {
				used += messageBytes(raw[i])
			}
			if used <= m.maxContextBytes {
				break
			}
			next := startIdx + 1
			for next < total && raw[next].Role != protocol.RoleUser {
				next++
			}
			if next >= total {
				break // 只剩最后一轮，保留
			}
			startIdx = next
		}
	}

	selected := raw[startIdx:]
	result := make([]protocol.Message, 0, len(selected)+1)
	if systemPrompt != "" {
		result = append(result, protocol.Message{Role: protocol.RoleSystem, Content: systemPrompt})
	}
	result = append(result, selected...)
	return result, nil
}

// messageBytes 估算单条消息的出站字符量（reasoning_content 不出站，不计入）
func messageBytes(m protocol.Message) int {
	n := len(m.Content)
	for _, tc := range m.ToolCalls {
		n += len(tc.Name) + len(tc.Arguments)
	}
	if m.ToolResult != nil {
		n += len(m.ToolResult.Content)
	}
	return n
}
