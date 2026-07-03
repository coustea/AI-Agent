import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  PptTemplateOption,
  ResourceGenerationRequest,
  ResourceTaskStatus,
} from '@/features/resource/model/resource'

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

/**
 * Fetch resource bundle with automatic retry.
 * Retries up to `retries` times with exponential backoff (1s, 2s, 4s).
 * Used when content is missing from polling summaries and needs recovery.
 */
export async function getResourceBundleWithRetry(
  resourceId: number,
  retries = 2,
): Promise<ReturnType<typeof getResourceBundle>> {
  let lastError: unknown
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await getResourceBundle(resourceId)
    } catch (err) {
      lastError = err
      if (attempt < retries) {
        await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt)))
      }
    }
  }
  throw lastError
}
