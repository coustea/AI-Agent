import http from '@/shared/utils/http'
import type { ApiResponse } from '@/shared/utils/http'
import type { PathLearningEvaluationResponse } from '@/learning/types/path'
import type {
  LearningEventCreate,
  LearningSessionCreate,
  LearningTimeStats,
} from '@/learning/types/evaluation'

export type {
  LearningEventCreate,
  LearningSessionCreate,
  LearningTimeStats,
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

export function getPathLearningEvaluation(pathId: number) {
  return http.get<ApiResponse<PathLearningEvaluationResponse | null>>(`/ai/path-plan/${pathId}/evaluation`)
}
