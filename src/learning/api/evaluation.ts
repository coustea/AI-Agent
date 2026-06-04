import http from '@/shared/utils/http'
import type { ApiResponse } from '@/shared/utils/http'
import type { PathLearningEvaluationResponse } from '@/learning/types/path'
import type {
  LearningEventCreate,
  LearningEventItem,
  LearningSessionCreate,
  LearningTimeStats,
} from '@/learning/types/evaluation'

export type {
  LearningEventCreate,
  LearningEventItem,
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

export function getEvaluationSummary(limit = 100) {
  return http.get<ApiResponse<Record<string, unknown>>>('/ai/evaluation/summary', { params: { limit } })
}

export function getLearningTimeStats(days = 30) {
  return http.get<ApiResponse<LearningTimeStats>>('/ai/evaluation/time-stats', { params: { days } })
}

export function getPathLearningEvaluation(pathId: number) {
  return http.get<ApiResponse<PathLearningEvaluationResponse | null>>(`/ai/path-plan/${pathId}/evaluation`)
}

export function getPathSummary(pathId: number) {
  return http.get<ApiResponse<Record<string, unknown> | null>>(`/ai/path-plan/${pathId}/summary`)
}
