import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  EvaluationSummary,
  LearningEventCreate,
  LearningSessionCreate,
  LearningTimeStats,
} from '@/features/evaluation/model/evaluation'

export type {
  EvaluationSummary,
  LearningEventCreate,
  LearningSessionCreate,
  LearningTimeStats,
}

export function recordLearningEvent(payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/events', payload)
}

export function recordLearningSession(payload: LearningSessionCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/sessions', payload)
}

export function recordPathLearningEvent(pathId: number, payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>(`/ai/path-plan/${pathId}/events`, payload)
}

export function getLearningTimeStats(days = 30) {
  return http.get<ApiResponse<LearningTimeStats>>('/ai/evaluation/time-stats', { params: { days } })
}

export function getEvaluationSummary(limit = 100) {
  return http.get<ApiResponse<EvaluationSummary>>('/ai/evaluation/summary', { params: { limit } })
}
