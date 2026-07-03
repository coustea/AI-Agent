export type LearningEventType =
  | 'resource_viewed'
  | 'resource_completed'
  | 'quiz_submitted'
  | 'path_feedback'
  | 'tutor_helpful'
  | 'resource_feedback'

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
  feedback?: string | null
  metadata?: Record<string, unknown>
}

export interface LearningSessionCreate {
  source_page: string
  started_at: string
  ended_at: string
  duration_seconds: number
  resource_id?: number | null
  path_id?: number | null
  path_node_id?: number | null
  node_id?: string | null
  course?: string | null
  topic?: string | null
  metadata?: Record<string, unknown>
}

export interface DailyTimeEntry {
  date: string
  seconds: number
}

export interface LearningTimeStats {
  today_seconds: number
  total_seconds: number
  streak_days: number
  daily_breakdown: DailyTimeEntry[]
  context_breakdown?: Record<string, number>
}

export interface LearningEventItem {
  id: number
  event_type: LearningEventType
  course?: string | null
  topic?: string | null
  feedback?: string | null
  created_at: string
}

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
