import http from '@/utils/http'
import type { ApiResponse } from '@/utils/http'
import type { PathLearningEvaluationResponse } from '@/path/api/path'

// ==========================================
// 类型定义
// ==========================================

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

// ==========================================
// 学习效果评估 API
// ==========================================

export function recordLearningEvent(payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/events', payload)
}

export function recordPathLearningEvent(pathId: number, payload: LearningEventCreate) {
  return http.post<ApiResponse<LearningEventItem>>(`/ai/path-plan/${pathId}/events`, payload)
}

export function getPathLearningEvaluation(pathId: number) {
  return http.get<ApiResponse<PathLearningEvaluationResponse>>(`/ai/path-plan/${pathId}/evaluation`)
}

export function getLearningTimeStats(days = 30) {
  return http.get<ApiResponse<LearningTimeStats>>('/ai/evaluation/time-stats', {
    params: { days },
  })
}