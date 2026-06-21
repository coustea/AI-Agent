import { readonly, ref, shallowRef } from 'vue'

import { subscribeAgentRun } from '@/shared/agent-events/api'
import type { AgentEvent, AgentRunStatus } from '@/shared/agent-events/model'

export type AgentConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'reconnecting'
  | 'completed'
  | 'failed'

export interface AgentRunHandlers {
  onEvent?: (event: AgentEvent) => void
  onContentDelta?: (delta: string, event: AgentEvent) => void
  onCompleted?: (event: AgentEvent) => void
  onFailed?: (error: Error, event: AgentEvent) => void
  onConnectionError?: (event: Event, willRetry: boolean) => void
}

export function useAgentRun() {
  const runId = ref<string | null>(null)
  const connectionStatus = ref<AgentConnectionStatus>('idle')
  const runStatus = ref<AgentRunStatus | null>(null)
  const events = ref<AgentEvent[]>([])
  const content = ref('')
  const progress = ref<number | null>(null)
  const title = ref('')
  const summary = ref('')
  const detail = ref<Record<string, unknown>>({})
  const error = shallowRef<Error | null>(null)
  const source = shallowRef<EventSource | null>(null)

  const close = () => {
    source.value?.close()
    source.value = null
  }

  const reset = () => {
    close()
    runId.value = null
    connectionStatus.value = 'idle'
    runStatus.value = null
    events.value = []
    content.value = ''
    progress.value = null
    title.value = ''
    summary.value = ''
    detail.value = {}
    error.value = null
  }

  const connect = (nextRunId: string, handlers: AgentRunHandlers = {}) => {
    reset()
    runId.value = nextRunId
    connectionStatus.value = 'connecting'

    const eventSource = subscribeAgentRun(nextRunId, {
      onEvent: (event) => {
        events.value = [...events.value, event]
        runStatus.value = event.status
        title.value = event.title
        summary.value = event.summary
        detail.value = event.detail
        if (event.progress != null) progress.value = event.progress

        if (event.type === 'content.delta') {
          const delta = String(event.detail.delta ?? '')
          content.value += delta
          handlers.onContentDelta?.(delta, event)
        }

        if (event.type === 'run.completed') {
          connectionStatus.value = 'completed'
          progress.value = 100
          handlers.onCompleted?.(event)
        } else if (event.type === 'run.failed') {
          connectionStatus.value = 'failed'
          error.value = new Error(event.summary || event.title || '智能体运行失败')
          handlers.onFailed?.(error.value, event)
        } else {
          connectionStatus.value = 'running'
        }

        handlers.onEvent?.(event)
      },
      onError: (connectionEvent) => {
        const willRetry = eventSource.readyState !== EventSource.CLOSED
        if (connectionStatus.value !== 'completed' && connectionStatus.value !== 'failed') {
          connectionStatus.value = willRetry ? 'reconnecting' : 'failed'
          if (!willRetry) error.value = new Error('智能体实时连接中断')
        }
        handlers.onConnectionError?.(connectionEvent, willRetry)
      },
    })

    source.value = eventSource
    return eventSource
  }

  return {
    runId: readonly(runId),
    connectionStatus: readonly(connectionStatus),
    runStatus: readonly(runStatus),
    events: readonly(events),
    content: readonly(content),
    progress: readonly(progress),
    title: readonly(title),
    summary: readonly(summary),
    detail: readonly(detail),
    error: readonly(error),
    connect,
    close,
    reset,
  }
}
