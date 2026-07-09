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

// 创建新学习路径：提交 topic/goal/current_knowledge/preferences → 后端启动多智能体规划
export function createLearningPath(payload: PathRequest) {
  return http.post<ApiResponse<CreatePathResponse>>('/ai/path-plan', payload)
}

// 获取当前激活的路径概览（含 stages + nodes 树形结构）
export function getCurrentLearningPath() {
  return http.get<ApiResponse<PathOverview | null>>('/ai/path-plan/active')
}

// 按 ID 查询指定路径的完整概览
export function getLearningPathById(pathId: number) {
  return http.get<ApiResponse<PathOverview>>(`/ai/path-plan/${pathId}`)
}

// 获取当前用户的历史路径列表
export function getLearningPathHistory() {
  return http.get<ApiResponse<LearningPathHistoryItem[]>>('/ai/path-plan/history')
}

// 切换到指定路径作为当前激活路径
export function activateLearningPath(pathId: number) {
  return http.post<ApiResponse<PathOverview>>(`/ai/path-plan/${pathId}/activate`)
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

// 以下 5 个为多智能体辅助资源生成接口（每个资源类型有独立的生成智能体）
export function generateMindmap(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/mindmap`, null, {
    timeout: 120000,
  })
}

export function generateCode(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/code`, null, {
    timeout: 120000,
  })
}

export function generatePpt(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/ppt`, null, {
    timeout: 120000,
  })
}

export function generateReading(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/reading`, null, {
    timeout: 120000,
  })
}

export function generateContent(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/content`)
}

export function generateCartoon(nodeId: number) {
  return http.post<ApiResponse<PathResourceDetail>>(`/ai/path-plan/nodes/${nodeId}/cartoon`, null, {
    timeout: 120000,
  })
}

// 查询已生成的辅助资源（生成前后都用它刷新状态）
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

// 获取路径学习评估报告：含画像快照、薄弱点、优化建议
export function getLearningEvaluation(pathId: number) {
  return http.get<ApiResponse<PathLearningEvaluationResponse | null>>(`/ai/path-plan/${pathId}/evaluation`)
}
