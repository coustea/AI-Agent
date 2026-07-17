// 行动计划项
export interface ActionPlanItem {
  topic: string
  action_type: 'review' | 'practice' | 'quiz'
  description: string
}

// 辅导策略结构 — 与后端 service.py 返回值对齐
export interface GuidanceStrategy {
  version: number
  conclusion: string // 本期结论文案（LLM 生成）
  focus_topics: string[]
  recommended_session_minutes: number
  tutoring_style: string
  action_plan: ActionPlanItem[]
  reason: string
}

// 学习评估 — 与后端 models.py LearningAssessment 对齐
export interface LearningAssessment {
  id: number
  user_id: number
  range_days: number
  status: 'generating' | 'ready' | 'failed'
  assessment: string | null
  generated_at: string | null
  failure_code: string | null
  created_at: string
}

// 历史评估列表响应
export interface AssessmentsHistoryResponse {
  items: Omit<LearningAssessment, 'assessment'>[]
  total: number
  page: number
  page_size: number
}

/**
 * 规范化辅导策略对象，处理可能缺失的字段
 */
export function normalizeGuidanceStrategy(strategy: Partial<GuidanceStrategy> | null | undefined): GuidanceStrategy | null {
  if (!strategy || Object.keys(strategy).length === 0) return null

  const normalized: GuidanceStrategy = {
    version: strategy.version ?? 1,
    conclusion: strategy.conclusion ?? '',
    focus_topics: Array.isArray(strategy.focus_topics) ? strategy.focus_topics : [],
    recommended_session_minutes: strategy.recommended_session_minutes ?? 25,
    tutoring_style: strategy.tutoring_style ?? '',
    action_plan: Array.isArray(strategy.action_plan) ? strategy.action_plan : [],
    reason: strategy.reason ?? '',
  }

  // 判断是否有有效内容
  const hasContent = Boolean(
    normalized.conclusion ||
    normalized.focus_topics.length ||
    normalized.action_plan.length ||
    normalized.tutoring_style,
  )

  return hasContent ? normalized : null
}
