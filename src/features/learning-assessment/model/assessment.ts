// 行动计划项
export interface ActionPlanItem {
  topic: string
  action_type: 'review' | 'practice' | 'quiz'
  description: string
  link: string
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

// ---------------------------------------------------------------------------
// 评估事实快照结构 —— 与后端 app/evaluation/facts.py 的 AssessmentFacts 对齐
// ---------------------------------------------------------------------------

export interface FactsWindow {
  days: number
  start: string
  end: string
}

export interface FactsDailyMinutes {
  date: string
  minutes: number
}

export interface FactsModuleCount {
  module: string
  count: number
}

export interface FactsActivity {
  active_days: number
  total_minutes: number
  daily_minutes: FactsDailyMinutes[]
  module_distribution: FactsModuleCount[]
}

export interface FactsResourceFeedback {
  helpful: number
  not_helpful: number
}

export interface FactsResourceUsage {
  generated: number
  viewed: number
  completed: number
  feedback: FactsResourceFeedback
}

export interface FactsLearningPath {
  nodes_started: number
  nodes_completed: number
  completion_rate: number
}

export interface FactsTopicPractice {
  topic: string
  submitted: number
  correct: number
  accuracy: number
  enough_evidence: boolean
}

export interface FactsPractice {
  submitted: number
  correct: number
  accuracy: number
  by_topic: FactsTopicPractice[]
}

export interface FactsTopics {
  encountered: string[]
}

export interface FactsDataQuality {
  has_activity: boolean
  insufficient_topics: string[]
}

export interface AssessmentFacts {
  window: FactsWindow
  activity: FactsActivity
  resource_usage: FactsResourceUsage
  learning_path: FactsLearningPath
  practice: FactsPractice
  topics: FactsTopics
  data_quality: FactsDataQuality
}

// 学习评估报告 — 与后端 models.py LearningAssessmentReport 对齐
export interface LearningAssessmentReport {
  id: number
  user_id: number
  range_days: 3 | 7 | 14
  window_start: string
  window_end: string
  status: 'generating' | 'ready' | 'failed'
  facts_snapshot?: AssessmentFacts | null
  report_markdown?: string | null
  generated_at?: string | null
  failure_code?: string | null
  created_at: string
  updated_at: string
}

// 历史报告列表响应
export interface ReportsHistoryResponse {
  items: Omit<LearningAssessmentReport, 'facts_snapshot' | 'report_markdown'>[]
  total: number
  page: number
  page_size: number
}

// 辅导策略 API 响应
export interface GuidanceStrategyResponse {
  guidance_strategy: Partial<GuidanceStrategy> | null
  guidance_updated_at: string | null
  last_assessment_report_id: number | null
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
