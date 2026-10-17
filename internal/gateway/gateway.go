// Package gateway 定义统一的大模型网关抽象与 OpenAI wire 协议实现。
// 核心数据模型（Message/Role/ToolCall/ToolResult/ToolDefinition/Usage/ChatRequest/ChatResponse）
// 统一定义在 internal/protocol 契约层中，本包只负责协议传输与多厂商路由。
package gateway

import (
	"context"
	"errors"

	"my-agent/internal/protocol"
)

var (
	ErrEmptyAPIKey   = errors.New("gateway: api key cannot be empty")
	ErrEmptyMessages = errors.New("gateway: messages cannot be empty")
)

// ChatRequest 统一采用 protocol.ChatRequest
type ChatRequest = protocol.ChatRequest

// StreamChunk 统一采用 protocol.ChatResponse
type StreamChunk = protocol.ChatResponse

// Gateway 统一 AI 网关接口
type Gateway interface {
	// ChatStream 执行流式调用，逐个 chunk 返回生成内容
	ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error)

	// TotalUsage 获取当前网关实例累计消耗的总 Token 用量
	TotalUsage() protocol.Usage
}
