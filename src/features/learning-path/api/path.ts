import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  PathRequest,
  CreatePathResponse,
  LearningPathHistoryItem,
  PathOverview,
  LearningPathWorkspace,
  PathQuizRound,
  PathQuizSubmitRequest,
  PathQuizSubmitResponse,
  PathResourceDetail,
  PathLearningEvaluationResponse,
} from '@/features/learning-path/model/path'

export type {
  PathRequest,
  CreatePathResponse,
  LearningPathHistoryItem,
  PathOverview,
  LearningPathWorkspace,
  PathQuizRound,
  PathQuizSubmitRequest,
  PathQuizSubmitResponse,
  PathResourceDetail,
  PathLearningEvaluationResponse,
}

export function createLearningPath(payload: PathRequest) {
  return http.post<ApiResponse<CreatePathResponse>>('/ai/path-plan', payload)
}

export function getCurrentLearningPath(module = 'mentor') {
  return http.get<ApiResponse<PathOverview | null>>('/ai/path-plan/active', {
    params: { module },
  })
}

export function getLearningPathById(pathId: number) {
  return http.get<ApiResponse<PathOverview>>(`/ai/path-plan/${pathId}`)
}

export function getLearningPathHistory(module = 'mentor') {
  return http.get<ApiResponse<LearningPathHistoryItem[]>>('/ai/path-plan/history', {
    params: { module },
  })
}

export function activateLearningPath(pathId: number) {
  return http.post<ApiResponse<PathOverview>>(`/ai/path-plan/${pathId}/activate`)
}

export function getLearningNodeWorkspace(nodeId: number) {
  return http.get<ApiResponse<LearningPathWorkspace>>(`/ai/path-plan/nodes/${nodeId}/workspace`)
}

export function startLearning(nodeId: number) {
  return http.post<ApiResponse<PathOverview>>(`/ai/path-plan/nodes/${nodeId}/start-learning`)
}

export function generateTutorial(nodeId: number) {
  return http.post<ApiResponse<LearningPathWorkspace>>(`/ai/path-plan/nodes/${nodeId}/tutorial`)
}

export function generateNodeQuestions(nodeId: number) {
  return http.post<ApiResponse<PathQuizRound>>(`/ai/path-plan/nodes/${nodeId}/questions`)
}

export function submitNodeQuiz(nodeId: number, payload: PathQuizSubmitRequest) {
  return http.post<ApiResponse<PathQuizSubmitResponse>>(`/ai/path-plan/nodes/${nodeId}/quiz-submit`, payload)
}

export function generateMindmap(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/mindmap`)
}

export function generateCode(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/code`)
}

export function generatePpt(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/ppt`)
}

export function generateReading(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/reading`)
}

export function generateContent(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/content`)
}

export function generateCartoon(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/cartoon`)
}

export function getMindmap(nodeId: number) {
  return http.get<ApiResponse<PathResourceDetail | null>>(`/ai/path-plan/nodes/${nodeId}/mindmap`)
}

export function getCode(nodeId: number) {
  return http.get<ApiResponse<PathResourceDetail | null>>(`/ai/path-plan/nodes/${nodeId}/code`)
}

export function getPpt(nodeId: number) {
  return http.get<ApiResponse<PathResourceDetail | null>>(`/ai/path-plan/nodes/${nodeId}/ppt`)
}

export function getReading(nodeId: number) {
  return http.get<ApiResponse<PathResourceDetail | null>>(`/ai/path-plan/nodes/${nodeId}/reading`)
}

export function getContent(nodeId: number) {
  return http.get<ApiResponse<PathResourceDetail | null>>(`/ai/path-plan/nodes/${nodeId}/content`)
}

export function getCartoon(nodeId: number) {
  return http.get<ApiResponse<PathResourceDetail | null>>(`/ai/path-plan/nodes/${nodeId}/cartoon`)
}

export function getLearningEvaluation(pathId: number) {
  return http.get<ApiResponse<PathLearningEvaluationResponse | null>>(`/ai/path-plan/${pathId}/evaluation`)
}
