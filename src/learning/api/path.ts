import http from '@/shared/utils/http'
import type { ApiResponse } from '@/shared/utils/http'
import type {
  AuxiliaryResourceRequest,
  CreateLearningPathRequest,
  LearningPathHistoryItem,
  LearningPathOverview,
  LearningPathWorkspace,
  PathQuizRound,
  PathQuizSubmitRequest,
  PathQuizSubmitResponse,
  PathResourceDetail,
} from '@/learning/types/path'

export type {
  AuxiliaryResourceRequest,
  CreateLearningPathRequest,
  LearningPathHistoryItem,
  LearningPathOverview,
  LearningPathWorkspace,
  PathQuizRound,
  PathQuizSubmitRequest,
  PathQuizSubmitResponse,
  PathResourceDetail,
}

export function createLearningPath(payload: CreateLearningPathRequest) {
  return http.post<ApiResponse<LearningPathOverview>>('/ai/path-plan', payload)
}

export function getCurrentLearningPath(module = 'mentor') {
  return http.get<ApiResponse<LearningPathOverview | null>>('/ai/path-plan/active', {
    params: { module },
  })
}

export function getLearningPathById(pathId: number) {
  return http.get<ApiResponse<LearningPathOverview>>(`/ai/path-plan/${pathId}`)
}

export function getLearningPathHistory(module = 'mentor') {
  return http.get<ApiResponse<LearningPathHistoryItem[]>>('/ai/path-plan/history', {
    params: { module },
  })
}

export function activateLearningPath(pathId: number) {
  return http.post<ApiResponse<LearningPathOverview>>(`/ai/path-plan/${pathId}/activate`)
}

export function getLearningNodeWorkspace(nodeId: number) {
  return http.get<ApiResponse<LearningPathWorkspace>>(`/ai/path-plan/nodes/${nodeId}/workspace`)
}

export function generateNodeQuestions(nodeId: number) {
  return http.post<ApiResponse<PathQuizRound>>(`/ai/path-plan/nodes/${nodeId}/questions`)
}

export function submitNodeQuiz(nodeId: number, payload: PathQuizSubmitRequest) {
  return http.post<ApiResponse<PathQuizSubmitResponse>>(`/ai/path-plan/nodes/${nodeId}/quiz-submit`, payload)
}

export function generateAuxiliaryResource(nodeId: number, payload: AuxiliaryResourceRequest) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/resources`, payload)
}
