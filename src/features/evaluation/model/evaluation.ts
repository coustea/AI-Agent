export type ModuleType = 'chat' | 'resource' | 'path' | 'quiz' | 'visualizer'

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

export interface LearningEventCreate {
  module: ModuleType
  entity_id?: string | null
  event_type: LearningEventType
  course?: string | null
  topic?: string | null
  score?: number | null
  event_metadata?: Record<string, unknown>
}

export interface LearningSessionCreate {
  source_page: string
  started_at: string
  ended_at: string
  duration_seconds: number
  course?: string | null
  topic?: string | null
  event_metadata?: Record<string, unknown>
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
  module: ModuleType
  entity_id?: string | null
  event_type: LearningEventType
  course?: string | null
  topic?: string | null
  score?: number | null
  event_metadata?: Record<string, unknown>
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
