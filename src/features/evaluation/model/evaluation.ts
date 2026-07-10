// 功能模块类型
export type ModuleType = 'chat' | 'resource' | 'path' | 'quiz' | 'visualizer'

// 学习事件类型枚举
export type LearningEventType =
  | 'chat_dialogue'
  | 'resource_generated'
  | 'resource_viewed'
  | 'resource_completed'
  | 'resource_feedback'
  | 'path_node_started'
  | 'path_node_completed'
  | 'path_quiz_answered'
  | 'path_feedback'
  | 'quiz_submitted'
  | 'visualizer_run'
  | 'tutor_helpful'

// 创建学习事件的请求参数
export interface LearningEventCreate {
  module: ModuleType
  entity_id?: string | null
  event_type: LearningEventType
  course?: string | null
  topic?: string | null
  score?: number | null
  event_metadata?: Record<string, unknown>
}

// 创建学习会话的请求参数
export interface LearningSessionCreate {
  source_page: string
  started_at: string
  ended_at: string
  duration_seconds: number
  course?: string | null
  topic?: string | null
  event_metadata?: Record<string, unknown>
}

// 每日学习时长记录
export interface DailyTimeEntry {
  date: string
  seconds: number
}

// 学习时间统计（总时长/连续天数/每日分布）
export interface LearningTimeStats {
  today_seconds: number
  total_seconds: number
  streak_days: number
  daily_breakdown: DailyTimeEntry[]
  context_breakdown?: Record<string, number>
}

// 学习事件记录项
export interface LearningEventItem {
  id: number
  module: ModuleType
  entity_id?: string | null
  event_type: LearningEventType
  course?: string | null
  topic?: string | null
  score?: number | null
  event_metadata?: Record<string, unknown>
  created_at: string
}

// 学习评估摘要（事件统计/弱项/推荐）
export interface EvaluationSummary {
  event_count: number
  average_score: number | null
  completed_resources: number
  viewed_resources: number
  weak_topics: string[]
  preferred_resources: string[]
  recommendations: string[]
  recent_events: LearningEventItem[]
}
