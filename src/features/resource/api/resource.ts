// src/features/resource/api/resource.ts — 资源生成模块 API 封装
import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  ResourceGenerationRequest,
  ResourceRunState,
  GeneratedResourceBundle,
  GeneratedResourceHistoryItem,
} from '@/features/resource/model/resource'

// 启动教学资源生成主 Agent 循环 POST /ai/resource/generate
export function startResourceGeneration(params: ResourceGenerationRequest) {
  return http.post<ApiResponse<{ run_id: string; resource_id: number }>>('/ai/resource/generate', params)
}

// 获取运行状态快照 GET /ai/resource/runs/:runId
export function getResourceRunSnapshot(runId: string) {
  return http.get<ApiResponse<ResourceRunState>>(`/ai/resource/runs/${runId}`)
}

// 取消正在进行的生成任务 POST /ai/resource/runs/:runId/cancel
export function cancelResourceRun(runId: string) {
  return http.post<ApiResponse<{ run_id: string; status: string }>>(`/ai/resource/runs/${runId}/cancel`)
}

// 获取完整产物包 GET /ai/resource/bundles/:resourceId
export function getResourceBundle(resourceId: number) {
  return http.get<ApiResponse<GeneratedResourceBundle>>(`/ai/resource/bundles/${resourceId}`, { timeout: 30000 })
}

// 获取历史生成列表 GET /ai/resources
export function getGeneratedResources(page = 1, limit = 20) {
  const offset = (page - 1) * limit
  return http.get<ApiResponse<{ items: GeneratedResourceHistoryItem[]; total: number }>>('/ai/resources', {
    params: { limit, offset },
  })
}
