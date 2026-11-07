// 功能模块类型
export type ModuleType = 'chat' | 'resource' | 'path' | 'quiz'

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

// 创建学习事件的请求参数
export interface LearningEventCreate {
  module: ModuleType
  entity_id?: string | null
  event_type: LearningEventType
  course?: string | null
  topic?: string | null
  score?: number | null
  event_metadata?: Record<string, unknown>
  client_event_id?: string | null
  occurred_at?: string
}

// 创建学习会话的请求参数（多态实体设计）
export interface LearningSessionCreate {
  source_page: string
  module?: string
  entity_id?: string | null
  sub_entity_id?: string | null
  started_at: string
  ended_at: string
  duration_seconds: number
  course?: string | null
  topic?: string | null
  event_metadata?: Record<string, unknown>
  client_session_id?: string | null
}
