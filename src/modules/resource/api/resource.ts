import http from '@/utils/http'
import type { ApiResponse } from '@/utils/http'
import type {
  ResourceAgentId,
  LearningScenario,
  ResourceGenerationRequest,
  ResourceTaskStatus,
  ResourceStreamEvent,
} from '@/types/resource'

// ==========================================
// 资源生成 SSE 流
// ==========================================

/**
 * 订阅资源生成的 SSE 事件流。
 * 使用 GET EventSource 连接到 /resources/{id}/events，接收 agent 状态变更和 done 信号。
 */
export function streamResourceEvents(
  resourceId: number,
  onEvent: (event: ResourceStreamEvent) => void,
  onDone: (event: ResourceStreamEvent) => void,
  onError: (error: unknown) => void,
): EventSource {
  const token = localStorage.getItem('token')
  const url = `/api/v1/ai/resources/${resourceId}/events${token ? `?token=${encodeURIComponent(token)}` : ''}`
  const es = new EventSource(url)

  es.addEventListener('agent', (e: MessageEvent) => {
    try {
      const data: ResourceStreamEvent = JSON.parse(e.data)
      onEvent(data)
    } catch (err) {
      console.error('Failed to parse agent event:', err)
    }
  })

  es.addEventListener('done', (e: MessageEvent) => {
    try {
      const data: ResourceStreamEvent = JSON.parse(e.data)
      onDone(data)
      es.close()
    } catch (err) {
      console.error('Failed to parse done event:', err)
    }
  })

  es.onerror = (err) => {
    onError(err)
    es.close()
  }

  return es
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
  return http.get<ApiResponse<any>>(`/ai/resources/${resourceId}/bundle`)
}

export function getResourceList(page = 1, pageSize = 10) {
  return http.get<ApiResponse<any>>('/ai/resources', {
    params: { page, page_size: pageSize },
  })
}

export function getResourceAgents() {
  return http.get<ApiResponse<any>>('/ai/resources/agents')
}
