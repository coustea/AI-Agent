package memory

import (
	"context"
	"strings"
	"sync"

	"my-agent/internal/gateway"
)

// SlidingWindowMemory 基于滑动窗口并严格保证轮次原子性（Turn Atomicity）的记忆实现。
// 裁剪历史时，保证 User -> Assistant(ToolCalls) -> Tool(ToolResult) 永远同生共死，绝不产生孤立的 RoleTool。
type SlidingWindowMemory struct {
	mu          sync.RWMutex
	messages    []gateway.Message
	maxMessages int
}

// NewSlidingWindowMemory 创建一个指定最大消息数量的滑动窗口记忆实例。
func NewSlidingWindowMemory(maxMessages int) *SlidingWindowMemory {
	if maxMessages <= 0 {
		maxMessages = 40
	}
	return &SlidingWindowMemory{
		messages:    make([]gateway.Message, 0),
		maxMessages: maxMessages,
	}
}

// Append 追加一条消息到记忆中。
func (m *SlidingWindowMemory) Append(ctx context.Context, msg gateway.Message) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.messages = append(m.messages, msg)
	return nil
}

// History 返回当前全部消息的副本。
func (m *SlidingWindowMemory) History() []gateway.Message {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return append([]gateway.Message(nil), m.messages...)
}

// Clear 清空记忆。
func (m *SlidingWindowMemory) Clear() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.messages = make([]gateway.Message, 0)
}

// BuildContext 构建准备发往模型的上下文序列，自动注入 systemPrompt 并按轮次原子性进行安全裁剪。
func (m *SlidingWindowMemory) BuildContext(ctx context.Context, systemPrompt string) ([]gateway.Message, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	raw := m.messages
	total := len(raw)

	systemPrompt = strings.TrimSpace(systemPrompt)

	if total == 0 {
		if systemPrompt != "" {
			return []gateway.Message{{Role: gateway.RoleSystem, Content: systemPrompt}}, nil
		}
		return []gateway.Message{}, nil
	}

	startIdx := 0
	if total > m.maxMessages {
		startIdx = total - m.maxMessages
	}

	// 轮次原子性回溯：
	// 确保切片的起点永远不是孤立的 RoleTool 或孤立的 RoleAssistant(ToolCalls)
	for startIdx > 0 {
		// 1. 如果起点落在 RoleTool，向前寻找发出该调用的 RoleAssistant
		if raw[startIdx].Role == gateway.RoleTool {
			startIdx--
			continue
		}
		// 2. 如果落在发起了 ToolCalls 的 RoleAssistant 上，进一步向前包含发起提问的 RoleUser
		if raw[startIdx].Role == gateway.RoleAssistant && len(raw[startIdx].ToolCalls) > 0 {
			if startIdx > 0 && raw[startIdx-1].Role == gateway.RoleUser {
				startIdx--
			}
			break
		}
		// 3. 如果已经对齐到完整的 RoleUser，对齐完毕
		if raw[startIdx].Role == gateway.RoleUser {
			break
		}
		startIdx--
	}

	selected := raw[startIdx:]
	result := make([]gateway.Message, 0, len(selected)+1)
	if systemPrompt != "" {
		result = append(result, gateway.Message{Role: gateway.RoleSystem, Content: systemPrompt})
	}
	result = append(result, selected...)
	return result, nil
}
