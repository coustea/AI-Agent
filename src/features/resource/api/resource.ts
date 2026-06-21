import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  ResourceGenerationRequest,
  ResourceTaskStatus,
} from '@/features/resource/model/resource'

// ==========================================
// 资源生成 API
// ==========================================

export function startResourceGeneration(params: ResourceGenerationRequest) {
  return http.post<ApiResponse<{ resource_id: number; run_id: string; status: string }>>('/ai/resources', params)
}

export function pollResourceStatus(resourceId: number) {
  return http.get<ApiResponse<ResourceTaskStatus>>(`/ai/resources/${resourceId}/status`)
}

export function getResourceBundle(resourceId: number) {
  return http.get<ApiResponse<any>>(`/ai/resources/${resourceId}`)
}
