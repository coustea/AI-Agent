import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  ResourceGenerationRequest,
  ResourceTaskStatus,
} from '@/features/resource/model/resource'

export interface PptTemplateOption {
  id: string
  name: string
  description: string
  family: string
  scheme: string
  tags: string[]
}

// ==========================================
// 资源生成 API
// ==========================================

export function startResourceGeneration(params: ResourceGenerationRequest) {
  return http.post<ApiResponse<{ resource_id: number; status: string }>>('/ai/resources', params)
}

export function pollResourceStatus(resourceId: number) {
  return http.get<ApiResponse<ResourceTaskStatus>>(`/ai/resources/${resourceId}/status`)
}

export function getResourceBundle(resourceId: number) {
  return http.get<ApiResponse<any>>(`/ai/resources/${resourceId}`, { timeout: 30000 })
}

export function getPptTemplates() {
  return http.get<ApiResponse<PptTemplateOption[]>>('/ai/ppt/templates')
}
