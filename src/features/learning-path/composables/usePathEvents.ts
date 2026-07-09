import { readonly, ref, shallowRef } from 'vue'
import type { PathEvent, PathEventName } from '@/features/learning-path/model/pathEvent'

// 路径规划 SSE 连接状态：idle → connecting → (running | reconnecting) → completed | failed
export type PathConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'reconnecting'
  | 'completed'
  | 'failed'

export interface PathEventHandlers {
  onEvent?: (event: PathEvent) => void        // 每次收到事件都会触发
  onNodeReady?: (event: PathEvent) => void     // 节点生成完成事件
  onCompleted?: (event: PathEvent) => void     // 路径规划完成
  onFailed?: (error: Error, event: PathEvent) => void
}

const API_BASE = '/api/v1/ai'

// 解析后端推送的 SSE 消息（JSON 格式），过滤无效/重复消息
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

  // 重置所有连接状态（关闭旧连接、清空事件队列）
  const reset = () => {
    close()
    runId.value = null
    pathId.value = null
    connectionStatus.value = 'idle'
    events.value = []
    error.value = null
    lastSequence.value = 0
  }

  // 建立 SSE 连接：监听后端多智能体路径规划/教程生成的实时事件流
  const connect = (nextPathId: number, nextRunId: string, handlers: PathEventHandlers = {}) => {
    reset()
    runId.value = nextRunId
    pathId.value = nextPathId
    connectionStatus.value = 'connecting'

    const url = `${API_BASE}/path-plan/${nextPathId}/runs/${nextRunId}/events`
    const eventSource = new EventSource(url)

    // 监听自定义事件 'path.event'（非标准 MessageEvent，需用 addEventListener）
    eventSource.addEventListener('path.event', (raw: MessageEvent) => {
      const event = parsePathEvent(raw)
      if (!event) return
      if (event.sequence <= lastSequence.value) return  // 去重：丢弃已处理过的旧序号
      lastSequence.value = event.sequence
      events.value = [...events.value, event]

      // 按事件类型分派：node.ready(节点生成完成) / planning.completed(规划完成) / planning.failed(失败)
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

    // 连接异常处理：EventSource 会自动重连，区分重连中 vs 彻底失败
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
