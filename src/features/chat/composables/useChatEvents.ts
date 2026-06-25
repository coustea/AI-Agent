// Chat 模块独立实时事件订阅 composable
// 连接到 /api/v1/ai/chat/sessions/{sessionId}/runs/{runId}/events

import { readonly, ref, shallowRef } from 'vue'

import type { ChatEvent, ChatEventName } from '@/features/chat/types/chatEvent'
import { getAuthToken } from '@/shared/auth/token'

export type ChatConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'reconnecting'
  | 'completed'
  | 'failed'

export interface ChatEventHandlers {
  onEvent?: (event: ChatEvent) => void
  onContentDelta?: (delta: string, event: ChatEvent) => void
  onToolStatus?: (event: ChatEvent) => void
  onDiagramReady?: (event: ChatEvent) => void
  onCompleted?: (event: ChatEvent) => void
  onFailed?: (error: Error, event: ChatEvent) => void
  onConnectionError?: (event: Event, willRetry: boolean) => void
}

const API_BASE = '/api/v1/ai'

function parseChatEvent(raw: MessageEvent): ChatEvent | null {
  try {
    const data = JSON.parse(raw.data)
    return {
      sequence: data.sequence,
      run_id: data.run_id,
      session_id: data.session_id,
      event: data.event as ChatEventName,
      message: data.message,
      data: data.data || {},
      timestamp: data.timestamp,
    }
  } catch {
    return null
  }
}

export function useChatEvents() {
  const runId = ref<string | null>(null)
  const sessionId = ref<string | null>(null)
  const connectionStatus = ref<ChatConnectionStatus>('idle')
  const events = ref<ChatEvent[]>([])
  const content = ref('')
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
    sessionId.value = null
    connectionStatus.value = 'idle'
    events.value = []
    content.value = ''
    error.value = null
    lastSequence.value = 0
  }

  const connect = (
    nextSessionId: string,
    nextRunId: string,
    handlers: ChatEventHandlers = {},
  ) => {
    reset()
    runId.value = nextRunId
    sessionId.value = nextSessionId
    connectionStatus.value = 'connecting'

    const token = getAuthToken()
    const query = token ? `?token=${encodeURIComponent(token)}` : ''
    const url = `${API_BASE}/chat/sessions/${nextSessionId}/runs/${nextRunId}/events${query}`
    const eventSource = new EventSource(url)

    eventSource.addEventListener('chat.event', (raw: MessageEvent) => {
      const event = parseChatEvent(raw)
      if (!event) return

      // 去重：只处理 sequence 递增的事件
      if (event.sequence <= lastSequence.value) return
      lastSequence.value = event.sequence

      events.value = [...events.value, event]

      // 内容增量
      if (event.event === 'content.delta') {
        const delta = String(event.data.delta ?? '')
        content.value += delta
        handlers.onContentDelta?.(delta, event)
      }

      // 工具状态
      if (
        event.event === 'tool.running' ||
        event.event === 'tool.completed' ||
        event.event === 'tool.failed'
      ) {
        handlers.onToolStatus?.(event)
      }

      // 图解就绪
      if (event.event === 'diagram.ready') {
        handlers.onDiagramReady?.(event)
      }

      // 终态
      if (event.event === 'run.completed') {
        connectionStatus.value = 'completed'
        handlers.onCompleted?.(event)
        close()
      } else if (event.event === 'run.failed') {
        connectionStatus.value = 'failed'
        error.value = new Error(event.message || '智能辅导运行失败')
        handlers.onFailed?.(error.value, event)
        close()
      } else {
        connectionStatus.value = 'running'
      }

      handlers.onEvent?.(event)
    })

    eventSource.onerror = (connectionEvent: Event) => {
      const willRetry = eventSource.readyState !== EventSource.CLOSED
      if (
        connectionStatus.value !== 'completed' &&
        connectionStatus.value !== 'failed'
      ) {
        connectionStatus.value = willRetry ? 'reconnecting' : 'failed'
        if (!willRetry) {
          error.value = new Error('智能辅导实时连接中断')
        }
      }
      handlers.onConnectionError?.(connectionEvent, willRetry)
    }

    source.value = eventSource
    return eventSource
  }

  return {
    runId: readonly(runId),
    sessionId: readonly(sessionId),
    connectionStatus: readonly(connectionStatus),
    events: readonly(events),
    content: readonly(content),
    error: readonly(error),
    lastSequence: readonly(lastSequence),
    connect,
    close,
    reset,
  }
}
