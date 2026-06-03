import http from '@/shared/utils/http'
import type { ApiResponse } from '@/shared/utils/http'
import type { PathLearningEvaluationResponse } from '@/learning/types/path'
import type {
  LearningEventType,
  LearningEventCreate,
  LearningEventItem,
  DailyTimeEntry,
  HourlyDistributionEntry,
  LearningTimeStats,
} from '@/learning/types/evaluation'

export type {
  LearningEventType,
  LearningEventCreate,
  LearningEventItem,
  DailyTimeEntry,
  HourlyDistributionEntry,
  LearningTimeStats,
}

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
