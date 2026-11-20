// Package turn 是一轮对话的编排者：整个系统的核心。
//
// 系统的设计单元是「一轮对话」而不是任何一层。一轮对话的生命周期固定为：
//
//	Acquire   加锁 + 归属校验 + 落库用户消息
//	Prepare   提取长期记忆 → 压缩上下文 → 重建窗口与 Prompt
//	Run       构建 Agent、流式执行、把增量推给订阅者
//	Commit    按终态落库 assistant 消息、回写上下文用量、触发标题生成
//
// 本包只输出「事件」而不是任何传输格式：SSE 之类的编码属于 httpapi 层。
// 这样同一套编排可以被 HTTP、CLI 或测试直接驱动，而无需伪造网络。
package turn

import (
	"errors"
	"time"
)

// 对外错误，供传输层映射状态码。
var (
	// ErrSessionNotFound 会话不存在或不属于该用户（统一 404，避免泄露存在性）
	ErrSessionNotFound = errors.New("会话不存在")
	// ErrBusy 会话正在生成中（409）
	ErrBusy = errors.New("会话正在生成中，请稍后再试")
	// ErrEmptyQuestion 问题为空（400）
	ErrEmptyQuestion = errors.New("问题内容不能为空")
	// ErrUnavailable 对话能力未启用（503）
	ErrUnavailable = errors.New("对话能力未启用")
	// ErrLockBusy 会话锁被占用（由 Lock 实现返回，编排层翻译成 ErrBusy）
	ErrLockBusy = errors.New("lock busy")
)

// EventKind 是事件类型。
type EventKind int

const (
	// EventDelta 增量文本
	EventDelta EventKind = iota
	// EventReset 要求客户端清空已渲染内容（工具调用前的过渡语作废）
	EventReset
	// EventDone 本轮结束，携带消息 id 与终态
	EventDone
	// EventError 本轮出错，携带面向用户的提示
	EventError
)

// Event 是本轮向外发出的一个事件。
//
// 刻意不用 sse.Frame：编排核心不该知道 HTTP 分帧格式。
// 传输层把它翻译成 SSE / WebSocket / 纯文本皆可。
type Event struct {
	Kind EventKind
	// Text 增量文本，仅 EventDelta / EventError 使用
	Text string
	// MessageID 落库后的 assistant 消息 id，仅 EventDone 使用
	MessageID uint64
	// Status 终态，仅 EventDone 使用
	Status string
}

// Sink 消费本轮事件。实现方必须快速返回，写失败应通过 ctx 取消本轮。
type Sink func(Event)

// Prepared 是一轮已经过校验并落库用户消息的对话。
type Prepared struct {
	UserID    string
	SessionID string
	Question  string

	// UserMsgID 本轮 user 消息 id，构建历史时需排除
	UserMsgID uint64
	// IsFirstTurn 是否会话首轮，用于触发标题生成
	IsFirstTurn bool

	// release 释放会话锁，由 Run 保证调用
	release func()
}

// Release 兜底释放锁。Run 内部已释放，这里是防御性调用（幂等）。
func (p *Prepared) Release() {
	if p != nil && p.release != nil {
		p.release()
		p.release = nil
	}
}

// Outcome 是一轮的最终结果，供测试与日志使用。
type Outcome struct {
	// Status 终态
	Status string
	// Content 落库的回答内容
	Content string
	// Elapsed 本轮耗时
	Elapsed time.Duration
	// Usage 模型返回的真实用量，nil 表示未返回
	Usage *TokenUsage
	// ToolCalls 本轮调用过的工具名
	ToolCalls []string
}

// TokenUsage 是模型返回的真实 token 用量。
// 与 chat.TokenUsage 分开定义，使本包不依赖存储层。
type TokenUsage struct {
	PromptTokens     int
	CompletionTokens int
	TotalTokens      int
}
