// 辅导策略结构
export interface GuidanceStrategy {
  version: number
  focus_topics: string[]
  preferred_resource_types: string[]
  recommended_session_minutes: number
  weekly_goal: string
  tutoring_style: string
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

export interface LearningAssessmentReport {
  id: number
  user_id: number
  range_days: 7 | 14 | 30
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

export interface ReportsHistoryResponse {
  items: Omit<LearningAssessmentReport, 'facts_snapshot' | 'report_markdown'>[]
  total: number
  page: number
  page_size: number
}

export interface GuidanceStrategyResponse {
  guidance_strategy: Partial<GuidanceStrategy> | null
  guidance_updated_at: string | null
  last_assessment_report_id: number | null
}

export function normalizeGuidanceStrategy(strategy: Partial<GuidanceStrategy> | null | undefined): GuidanceStrategy | null {
  if (!strategy || Object.keys(strategy).length === 0) return null

  const normalized: GuidanceStrategy = {
    version: strategy.version ?? 1,
    focus_topics: Array.isArray(strategy.focus_topics) ? strategy.focus_topics : [],
    preferred_resource_types: Array.isArray(strategy.preferred_resource_types) ? strategy.preferred_resource_types : [],
    recommended_session_minutes: strategy.recommended_session_minutes ?? 25,
    weekly_goal: strategy.weekly_goal ?? '',
    tutoring_style: strategy.tutoring_style ?? '',
    reason: strategy.reason ?? '',
  }

  const hasContent = Boolean(
    normalized.focus_topics.length ||
    normalized.preferred_resource_types.length ||
    normalized.weekly_goal ||
    normalized.tutoring_style ||
    normalized.reason,
  )

  return hasContent ? normalized : null
}
