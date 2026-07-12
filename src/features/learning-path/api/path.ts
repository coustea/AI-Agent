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
  PathResourceTaskResponse,
  PathLearningEvaluationResponse,
} from '@/features/learning-path/model/path'

// 创建新学习路径：提交 topic/goal/current_knowledge/preferences → 后端启动多智能体规划
export function createLearningPath(payload: PathRequest) {
  return http.post<ApiResponse<CreatePathResponse>>('/ai/path-plan', payload)
}

// 获取最近更新的可继续学习路径概览
export function getCurrentLearningPath() {
  return http.get<ApiResponse<PathOverview | null>>('/ai/path-plan/latest')
}

// 按 ID 查询指定路径的完整概览
export function getLearningPathById(pathId: number) {
  return http.get<ApiResponse<PathOverview>>(`/ai/path-plan/${pathId}`)
}

// 获取当前用户的历史路径列表
export function getLearningPathHistory() {
  return http.get<ApiResponse<LearningPathHistoryItem[]>>('/ai/path-plan/history')
}

// 获取节点工作空间：含当前教程、所有教程列表、资源列表、题目轮次信息
export function getLearningNodeWorkspace(nodeId: number) {
  return http.get<ApiResponse<LearningPathWorkspace>>(`/ai/path-plan/nodes/${nodeId}/workspace`)
}

// 标记开始学习节点（轻量记录，不阻塞后续教程生成）
export function startLearning(nodeId: number) {
  return http.post<ApiResponse<PathOverview>>(`/ai/path-plan/nodes/${nodeId}/start-learning`)
}

// 生成节点主教程（LLM 调用，耗时 15-30s+ → timeout 设为 3 分钟）
export function generateTutorial(nodeId: number) {
  return http.post<ApiResponse<LearningPathWorkspace>>(`/ai/path-plan/nodes/${nodeId}/tutorial`, null, {
    timeout: 180000,
  })
}

// 获取已有测验题目（GET，不重新生成，无题目时返回 null）
export function getNodeQuestions(nodeId: number) {
  return http.get<ApiResponse<PathQuizRound | null>>(`/ai/path-plan/nodes/${nodeId}/questions`)
}

// 生成节点测验（固定 5 道选择题，围绕当前教程知识点）
export function generateNodeQuestions(nodeId: number) {
  return http.post<ApiResponse<PathQuizRound>>(`/ai/path-plan/nodes/${nodeId}/questions`, null, {
    timeout: 120000,
  })
}

// 提交节点测验答案 → 后端判分，返回 outcome(completed/remediation/completed_with_gaps) + 薄弱点
export function submitNodeQuiz(nodeId: number, payload: PathQuizSubmitRequest) {
  return http.post<ApiResponse<PathQuizSubmitResponse>>(`/ai/path-plan/nodes/${nodeId}/quiz-submit`, payload)
}

// 生成节点辅助资源（统一接口）
const RESOURCE_TYPES = ['mindmap', 'code', 'ppt', 'reading', 'cartoon'] as const
type ResourceType = (typeof RESOURCE_TYPES)[number]

export function generateNodeResource(nodeId: number, resourceType: ResourceType) {
  return http.post<ApiResponse<PathResourceTaskResponse>>(
    `/ai/path-plan/nodes/${nodeId}/resources/${resourceType}`,
    null,
    { timeout: 30000 }
  )
}

// 获取路径学习评估报告：含画像快照、薄弱点、优化建议
export function getLearningEvaluation(pathId: number) {
  return http.get<ApiResponse<PathLearningEvaluationResponse | null>>(`/ai/path-plan/${pathId}/evaluation`)
}
