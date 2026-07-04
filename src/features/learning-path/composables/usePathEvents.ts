import { readonly, ref, shallowRef } from 'vue'
import type { PathEvent, PathEventName } from '@/features/learning-path/model/pathEvent'

export type PathConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'reconnecting'
  | 'completed'
  | 'failed'

export interface PathEventHandlers {
  onEvent?: (event: PathEvent) => void
  onNodeReady?: (event: PathEvent) => void
  onCompleted?: (event: PathEvent) => void
  onFailed?: (error: Error, event: PathEvent) => void
}

const API_BASE = '/api/v1/ai'

function parsePathEvent(raw: MessageEvent): PathEvent | null {
  try {
    const data = JSON.parse(raw.data)
    return {
      sequence: data.sequence,
      run_id: data.run_id,
      path_id: data.path_id,
      event: data.event as PathEventName,
      stage: data.stage,
      message: data.message,
      progress: data.progress,
      data: data.data || {},
      timestamp: data.timestamp,
    }
  } catch {
    return null
  }
}

export function usePathEvents() {
  const runId = ref<string | null>(null)
  const pathId = ref<number | null>(null)
  const connectionStatus = ref<PathConnectionStatus>('idle')
  const events = ref<PathEvent[]>([])
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
    pathId.value = null
    connectionStatus.value = 'idle'
    events.value = []
    error.value = null
    lastSequence.value = 0
  }

  const connect = (nextPathId: number, nextRunId: string, handlers: PathEventHandlers = {}) => {
    reset()
    runId.value = nextRunId
    pathId.value = nextPathId
    connectionStatus.value = 'connecting'

    const url = `${API_BASE}/path-plan/${nextPathId}/runs/${nextRunId}/events`
    const eventSource = new EventSource(url)

    eventSource.addEventListener('path.event', (raw: MessageEvent) => {
      const event = parsePathEvent(raw)
      if (!event) return
      if (event.sequence <= lastSequence.value) return
      lastSequence.value = event.sequence
      events.value = [...events.value, event]

      if (event.event === 'node.ready') {
        handlers.onNodeReady?.(event)
      }
      if (event.event === 'planning.completed') {
        connectionStatus.value = 'completed'
        handlers.onCompleted?.(event)
        close()
      } else if (event.event === 'planning.failed') {
        connectionStatus.value = 'failed'
        error.value = new Error(event.message || '路径规划失败')
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
    pathId: readonly(pathId),
    connectionStatus: readonly(connectionStatus),
    events: readonly(events),
    error: readonly(error),
    lastSequence: readonly(lastSequence),
    connect,
    close,
    reset,
  }
}
