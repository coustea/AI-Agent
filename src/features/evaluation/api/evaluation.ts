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

// 记录学习事件（答题/浏览等）
export function recordLearningEvent(payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/events', payload)
}

// 记录学习会话（单次学习时长）
export function recordLearningSession(payload: LearningSessionCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/sessions', payload)
}

// 记录学习路径相关事件（关联 pathId）
export function recordPathLearningEvent(pathId: number, payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>(`/ai/path-plan/${pathId}/events`, payload)
}

// 获取学习时间统计（默认近 30 天）
export function getLearningTimeStats(days = 30) {
  return http.get<ApiResponse<LearningTimeStats>>('/ai/evaluation/time-stats', { params: { days } })
}

// 获取学习评估摘要（弱项/推荐等）
export function getEvaluationSummary(limit = 100) {
  return http.get<ApiResponse<EvaluationSummary>>('/ai/evaluation/summary', { params: { limit } })
}
