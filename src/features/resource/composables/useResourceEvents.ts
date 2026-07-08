import { readonly, ref, shallowRef } from 'vue'
import type { ResourceEvent, ResourceEventName } from '@/features/resource/model/resourceEvent'
// 获取当前用户 JWT token，用于 SSE 鉴权
import { getAuthToken } from '@/shared/auth/token'

// SSE 连接生命周期状态：空闲 → 连接中 → 运行中 / 重连中 → 完成 / 失败
export type ResourceConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'reconnecting'
  | 'completed'
  | 'failed'

// 外部可注册的事件回调集合，按事件类型分别触发
export interface ResourceEventHandlers {
  onEvent?: (event: ResourceEvent) => void
  onAgentStatus?: (event: ResourceEvent) => void
  onArtifactReady?: (event: ResourceEvent) => void
  onCompleted?: (event: ResourceEvent) => void
  onFailed?: (error: Error, event: ResourceEvent) => void
}

// 资源事件 SSE 接口基础路径
const API_BASE = '/api/v1/ai'

// 将 SSE 原始 MessageEvent 解析为结构化 ResourceEvent，解析失败返回 null
function parseResourceEvent(raw: MessageEvent): ResourceEvent | null {
  try {
    const data = JSON.parse(raw.data)
    return {
      sequence: data.sequence,
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

// 资源事件流组合式函数：管理 SSE EventSource 连接、事件去重、重连与状态回调
export function useResourceEvents() {
  // 当前连接的资源 id
  const resourceId = ref<number | null>(null)
  // SSE 连接状态
  const connectionStatus = ref<ResourceConnectionStatus>('idle')
  // 已接收的事件列表（只读暴露给外部）
  const events = ref<ResourceEvent[]>([])
  // 连接错误对象
  const error = shallowRef<Error | null>(null)
  // 底层 EventSource 实例
  const source = shallowRef<EventSource | null>(null)
  // 最近处理过的事件序号，用于断线重连时跳过重复事件
  const lastSequence = ref(0)

  // 关闭当前 SSE 连接并清空引用
  const close = () => {
    source.value?.close()
    source.value = null
  }

  // 完全重置状态：关闭连接、清空事件和序号，回到初始空闲态
  const reset = () => {
    close()
    resourceId.value = null
    connectionStatus.value = 'idle'
    events.value = []
    error.value = null
    lastSequence.value = 0
  }

  // 建立资源事件 SSE 连接，按事件类型分发到对应回调
  const connect = (nextResourceId: number, handlers: ResourceEventHandlers = {}) => {
    // 判断是否为同一资源的重连：重连时保留已有事件历史
    const reconnectingSameResource = resourceId.value === nextResourceId
    close()
    if (!reconnectingSameResource) {
      events.value = []
      lastSequence.value = 0
    }
    resourceId.value = nextResourceId
    connectionStatus.value = 'connecting'
    error.value = null

    // 构建带鉴权 token 和断点续传 after_sequence 参数的查询串
    const params = new URLSearchParams()
    const token = getAuthToken()
    if (token) params.set('token', token)
    // 断线重连时从上次序号继续，避免重复事件
    if (lastSequence.value > 0) params.set('after_sequence', String(lastSequence.value))
    const query = params.toString()
    const url = `${API_BASE}/resources/${nextResourceId}/events${query ? `?${query}` : ''}`
    const eventSource = new EventSource(url)

    // 监听服务端推送的资源事件消息
    eventSource.addEventListener('resource.event', (raw: MessageEvent) => {
      const event = parseResourceEvent(raw)
      if (!event) return
      // 序号去重：跳过已处理过的事件
      if (event.sequence <= lastSequence.value) return
      lastSequence.value = event.sequence
      events.value = [...events.value, event]

      // 智能体状态变更事件单独触发回调
      if (event.event === 'agent.status') {
        handlers.onAgentStatus?.(event)
      }
      // 生成完成：标记终态、触发回调并关闭连接
      if (event.event === 'generation.completed') {
        connectionStatus.value = 'completed'
        handlers.onCompleted?.(event)
        close()
      } else if (event.event === 'generation.failed') {
        // 生成失败：标记终态、设置错误并触发回调
        connectionStatus.value = 'failed'
        error.value = new Error(event.message || '资源生成失败')
        handlers.onFailed?.(error.value, event)
        close()
      } else {
        // 其他事件标记为运行中状态
        connectionStatus.value = 'running'
      }
      // 所有事件统一触发通用回调
      handlers.onEvent?.(event)
    })

    // SSE 连接错误处理：根据 readyState 判断是否自动重连
    eventSource.onerror = () => {
      const willRetry = eventSource.readyState !== EventSource.CLOSED
      if (connectionStatus.value !== 'completed' && connectionStatus.value !== 'failed') {
        connectionStatus.value = willRetry ? 'reconnecting' : 'failed'
      }
    }

    source.value = eventSource
    return eventSource
  }

  // 返回只读状态（防止外部直接修改）和连接管理方法
  return {
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
