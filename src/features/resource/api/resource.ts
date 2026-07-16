// 封装带 JWT 拦截的 axios 实例与统一响应信封类型
import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
// 引入资源生成请求体类型与任务状态类型，保持前后端字段对齐
import type {
  ResourceGenerationRequest,
  GeneratedResourceBundle,
  GeneratedResourceHistoryItem,
  ResourceLifecycleStatus,
  ResourceTaskStatus,
} from '@/features/resource/model/resource'

// ==========================================
// 资源生成 API
// ==========================================

// 发起资源生成任务 POST /ai/resources，请求体为 ResourceGenerationRequest
export function startResourceGeneration(params: ResourceGenerationRequest) {
  return http.post<ApiResponse<{ resource_id: number; status: ResourceLifecycleStatus }>>('/ai/resources', params)
}

// 轮询资源生成任务状态 GET /ai/resources/:resourceId/status
export function pollResourceStatus(resourceId: number) {
  return http.get<ApiResponse<ResourceTaskStatus>>(`/ai/resources/${resourceId}/status`)
}

// 获取资源生成任务的完整产物包 GET /ai/resources/:resourceId（超时 30s 以应对大产物）
export function getResourceBundle(resourceId: number) {
  return http.get<ApiResponse<GeneratedResourceBundle>>(`/ai/resources/${resourceId}`, { timeout: 30000 })
}

// 分页获取独立资源生成历史
export function getGeneratedResources(page = 1, limit = 20) {
  const offset = (page - 1) * limit
  return http.get<ApiResponse<{ items: GeneratedResourceHistoryItem[]; total: number }>>('/ai/resources', {
    params: { limit, offset },
  })
}

