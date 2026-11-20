package memory

import "time"

// Config 是 Pre-Run 记忆策略的全部可调参数。
// 由 config.ChatConfig 转换而来，本包不直接依赖全局配置。
type Config struct {
	// HistoryMaxMessages 送入模型的历史消息条数上限
	HistoryMaxMessages int
	// HistoryBudgetTokens 历史 token 预算
	HistoryBudgetTokens int
	// CompressTriggerTokens 触发压缩的 token 阈值
	CompressTriggerTokens int
	// CompressTriggerMessages 触发压缩的消息条数阈值
	CompressTriggerMessages int
	// CompressSourceMaxChars 单次送入压缩的原文最大字符数
	CompressSourceMaxChars int
	// KeepRecentTurns 压缩时保留原文的最近轮数
	KeepRecentTurns int
	// MemoryMinTurns 触发记忆提取的轮数阈值
	MemoryMinTurns int
	// MemoryMinTokens 触发记忆提取的 token 阈值
	MemoryMinTokens int
	// MemoryMaxChars 长期记忆文档最大字符数
	MemoryMaxChars int
	// WorkspaceRoot 会话工作目录根路径，用于生成工作区文件索引
	WorkspaceRoot string
	// LLMTimeout 单次 LLM 调用（压缩/整合）超时
	LLMTimeout time.Duration
}

// withDefaults 填充零值，保证测试与生产都不会因零值除零或永远不触发。
func (c Config) withDefaults() Config {
	if c.HistoryMaxMessages <= 0 {
		c.HistoryMaxMessages = 40
	}
	if c.HistoryBudgetTokens <= 0 {
		c.HistoryBudgetTokens = 12000
	}
	if c.CompressTriggerTokens <= 0 {
		c.CompressTriggerTokens = 6000
	}
	if c.CompressTriggerMessages <= 0 {
		c.CompressTriggerMessages = 16
	}
	if c.CompressSourceMaxChars <= 0 {
		c.CompressSourceMaxChars = 8000
	}
	if c.KeepRecentTurns <= 0 {
		c.KeepRecentTurns = 2
	}
	if c.MemoryMinTurns <= 0 {
		c.MemoryMinTurns = 4
	}
	if c.MemoryMinTokens <= 0 {
		c.MemoryMinTokens = 4000
	}
	if c.MemoryMaxChars <= 0 {
		c.MemoryMaxChars = 2000
	}
	if c.LLMTimeout <= 0 {
		c.LLMTimeout = 120 * time.Second
	}
	return c
}
