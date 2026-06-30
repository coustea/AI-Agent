import { readonly, ref, shallowRef } from 'vue'
import type { ResourceEvent, ResourceEventName } from '@/features/resource/model/resourceEvent'
import { getAuthToken } from '@/shared/auth/token'

export type ResourceConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'reconnecting'
  | 'completed'
  | 'failed'

export interface ResourceEventHandlers {
  onEvent?: (event: ResourceEvent) => void
  onAgentStatus?: (event: ResourceEvent) => void
  onArtifactReady?: (event: ResourceEvent) => void
  onCompleted?: (event: ResourceEvent) => void
  onFailed?: (error: Error, event: ResourceEvent) => void
}

const API_BASE = '/api/v1/ai'

function parseResourceEvent(raw: MessageEvent): ResourceEvent | null {
  try {
    const data = JSON.parse(raw.data)
    return {
      sequence: data.sequence,
      run_id: data.run_id,
      resource_id: data.resource_id,
      event: data.event as ResourceEventName,
      agent_id: data.agent_id,
      message: data.message,
      progress: data.progress,
      data: data.data || {},
      timestamp: data.timestamp,
    }
  } catch {
    return null
  }
}

export function useResourceEvents() {
  const runId = ref<string | null>(null)
  const resourceId = ref<number | null>(null)
  const connectionStatus = ref<ResourceConnectionStatus>('idle')
  const events = ref<ResourceEvent[]>([])
  const error = shallowRef<Error | null>(null)
  const source = shallowRef<EventSource | null>(null)
  const lastSequence = ref(0)

  const close = () => {
    source.value?.close()
    source.value = null
  }

  const reset = () => {
    close()
    runId.value = null
    resourceId.value = null
    connectionStatus.value = 'idle'
    events.value = []
    error.value = null
    lastSequence.value = 0
  }

  const connect = (nextResourceId: number, nextRunId: string, handlers: ResourceEventHandlers = {}) => {
    const reconnectingSameRun = (
      resourceId.value === nextResourceId
      && runId.value === nextRunId
    )
    close()
    if (!reconnectingSameRun) {
      events.value = []
      lastSequence.value = 0
    }
    runId.value = nextRunId
    resourceId.value = nextResourceId
    connectionStatus.value = 'connecting'
    error.value = null

    const params = new URLSearchParams()
    const token = getAuthToken()
    if (token) params.set('token', token)
    if (lastSequence.value > 0) params.set('after_sequence', String(lastSequence.value))
    const query = params.toString()
    const url = `${API_BASE}/resources/${nextResourceId}/events${query ? `?${query}` : ''}`
    const eventSource = new EventSource(url)

    eventSource.addEventListener('resource.event', (raw: MessageEvent) => {
      const event = parseResourceEvent(raw)
      if (!event) return
      if (event.sequence <= lastSequence.value) return
      lastSequence.value = event.sequence
      events.value = [...events.value, event]

      if (event.event === 'agent.status') {
        handlers.onAgentStatus?.(event)
      }
      if (event.event === 'generation.completed') {
        connectionStatus.value = 'completed'
        handlers.onCompleted?.(event)
        close()
      } else if (event.event === 'generation.failed') {
        connectionStatus.value = 'failed'
        error.value = new Error(event.message || '资源生成失败')
        handlers.onFailed?.(error.value, event)
        close()
      } else {
        connectionStatus.value = 'running'
      }
      handlers.onEvent?.(event)
    })

    eventSource.onerror = () => {
      const willRetry = eventSource.readyState !== EventSource.CLOSED
      if (connectionStatus.value !== 'completed' && connectionStatus.value !== 'failed') {
        connectionStatus.value = willRetry ? 'reconnecting' : 'failed'
      }
    }

    source.value = eventSource
    return eventSource
  }

  return {
    runId: readonly(runId),
    resourceId: readonly(resourceId),
    connectionStatus: readonly(connectionStatus),
    events: readonly(events),
    error: readonly(error),
    lastSequence: readonly(lastSequence),
    connect,
    close,
    reset,
  }
}
