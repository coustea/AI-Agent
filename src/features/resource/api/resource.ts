import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import { getAuthToken } from '@/shared/auth/token'
import type {
  ResourceGenerationRequest,
  ResourceTaskStatus,
  ResourceStreamEvent,
} from '@/features/resource/model/resource'

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
  const token = getAuthToken()
  const url = `/api/v1/ai/resources/${resourceId}/events${token ? `?token=${encodeURIComponent(token)}` : ''}`
  const es = new EventSource(url)

  const handleAgentLikeEvent = (e: MessageEvent) => {
    try {
      const data: ResourceStreamEvent = JSON.parse(e.data)
      onEvent(data)
    } catch (err) {
      console.error('Failed to parse agent event:', err)
    }
  }

  ;[
    'agent',
    'agent.snapshot',
    'agent.step',
    'agent.heartbeat',
    'agent.metric',
    'agent.artifact_ready',
  ].forEach((eventName) => {
    es.addEventListener(eventName, handleAgentLikeEvent)
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
  return http.get<ApiResponse<any>>(`/ai/resources/${resourceId}`)
}
