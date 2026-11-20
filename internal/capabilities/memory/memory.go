// Package memory 提供跨会话的长期记忆。
//
// 设计边界（重要）：
//   - 只保存用户明确要求记住、或明确授权的信息；
//   - 不做用户画像推断，不做学习能力建模；
//   - 检索用 MySQL 关键词匹配，不引入向量库。
//
// 记忆与历史消息完全分离：历史消息属于会话，由 Harness 加载；
// 记忆属于用户，由 Agent 通过工具按需检索。
package memory

import (
	"time"
)

// 记忆类别，用于分组展示与检索加权。
const (
	KindFact       = "fact"       // 客观事实：专业、年级、目标
	KindPreference = "preference" // 偏好：讲解风格、语言、深度
	KindWeakness   = "weakness"   // 薄弱点
	KindGoal       = "goal"       // 目标
)

// Memory 是一条长期记忆。
type Memory struct {
	ID     string
	UserID string
	Kind   string
	// Content 记忆正文，一条只说一件事
	Content string
	// Source 来源：用户显式要求(explicit) / Agent 归纳(inferred)
	Source string
	// ConversationID 首次记录的会话，便于追溯
	ConversationID string
	CreatedAt      time.Time
	UpdatedAt      time.Time
}

// normalizeKind 把未知类别归到 fact，避免脏数据进入分类统计。
func normalizeKind(k string) string {
	// 常量值本身就是合法输入（"preference" 等），
	// 因此 case 必须同时覆盖常量与常见别名。
	switch k {
	case KindPreference, "prefer", "style", "偏好":
		return KindPreference
	case KindWeakness, "weak", "gap", "薄弱":
		return KindWeakness
	case KindGoal, "target", "plan", "目标":
		return KindGoal
	case KindFact, "事实", "":
		return KindFact
	default:
		return KindFact
	}
}
