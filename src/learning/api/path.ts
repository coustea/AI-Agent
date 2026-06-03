import http from '@/shared/utils/http'
import type { ApiResponse } from '@/shared/utils/http'
import type {
  AgentStage,
  CoursePathNodeDTO,
  CoursePathResponse,
  CoursePathSummaryResponse,
  LearningSignalSnapshot,
  PathLearningEvaluationResponse,
  PathPlanFeedbackRequest,
  GenerateCoursePathParams,
  PathGenerationTaskResponse,
  PathNodeResourceRequest,
} from '@/learning/types/path'

export type {
  AgentStage,
  CoursePathNodeDTO,
  CoursePathResponse,
  CoursePathSummaryResponse,
  LearningSignalSnapshot,
  PathLearningEvaluationResponse,
  PathPlanFeedbackRequest,
  GenerateCoursePathParams,
  PathGenerationTaskResponse,
  PathNodeResourceRequest,
}

export function getPathPlan() {
  return getActiveCoursePath()
}

export function adjustCoursePath(payload: PathPlanFeedbackRequest) {
  return http.patch<ApiResponse<CoursePathResponse>>('/ai/path-plan', payload)
}

export function getActiveCoursePath(module = 'mentor') {
  return http.get<ApiResponse<CoursePathResponse>>('/ai/path-plan/active', {
    params: { module },
  })
}

export function generateCoursePath(params: GenerateCoursePathParams) {
  return http.post<ApiResponse<PathGenerationTaskResponse>>('/ai/path-plan/generate', params)
}

export function getActiveCoursePathTask(module = 'mentor') {
  return http.get<ApiResponse<PathGenerationTaskResponse | null>>('/ai/path-plan/tasks/active', {
    params: { module },
  })
}

export function getCoursePathTaskStatus(taskId: number) {
  return http.get<ApiResponse<PathGenerationTaskResponse>>(`/ai/path-plan/tasks/${taskId}/status`)
}

export function generatePathNodeResources(
  nodeId: number,
  payload: PathNodeResourceRequest,
) {
  return http.post<ApiResponse<{ resource_id: number; node_id: number; status: string }>>(
    `/ai/path-plan/nodes/${nodeId}/generate-resources`,
    payload,
  )
}

export function startCoursePathNode(nodeId: number) {
  return http.post<ApiResponse<CoursePathResponse>>(`/ai/path-plan/nodes/${nodeId}/start`)
}

export function completeCoursePathNode(nodeId: number) {
  return http.post<ApiResponse<CoursePathResponse>>(`/ai/path-plan/nodes/${nodeId}/complete`)
}

export function getCoursePathSummary(pathId: number) {
  return http.get<ApiResponse<CoursePathSummaryResponse | null>>(`/ai/path-plan/${pathId}/summary`)
}
