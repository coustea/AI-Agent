export type LearningEventType =
  | 'resource_viewed'
  | 'resource_completed'
  | 'quiz_submitted'
  | 'path_feedback'
  | 'tutor_helpful'
  | 'resource_feedback'
  | 'learning_heartbeat'

export interface LearningEventCreate {
  event_type: LearningEventType
  session_id?: string | null
  resource_id?: number | null
  resource_item_id?: number | null
  path_id?: number | null
  path_node_id?: number | null
  node_id?: string | null
  course?: string | null
  topic?: string | null
  score?: number | null
  duration_seconds?: number | null
  feedback?: string | null
  metadata?: Record<string, unknown>
}

export interface LearningEventItem {
  id: number
  event_type: string
  resource_id: number | null
  resource_item_id: number | null
  path_id: number | null
  path_node_id: number | null
  node_id: string | null
  course: string | null
  topic: string | null
  score: number | null
  duration_seconds: number | null
  feedback: string | null
  created_at: string
}

export interface DailyTimeEntry {
  date: string
  seconds: number
}

export interface HourlyDistributionEntry {
  hour: number
  seconds: number
}

export interface LearningTimeStats {
  today_seconds: number
  week_seconds: number
  month_seconds: number
  total_seconds: number
  streak_days: number
  daily_breakdown: DailyTimeEntry[]
  hourly_distribution: HourlyDistributionEntry[]
  context_breakdown?: Record<string, number>
}

export interface QuizBankQuestion {
  id: string
  subject: string
  subject_en?: string | null
  type: string
  difficulty?: string | null
  content: string
  options?: Record<string, string> | null
  answer: string
  analysis: string
  knowledge_points: string[]
  tags: string[]
  language?: string | null
  split?: string | null
}

export interface QuizBankQuestionListResponse {
  items: QuizBankQuestion[]
  total: number
  page: number
  page_size: number
  subjects: string[]
  difficulties: string[]
  types: string[]
}
