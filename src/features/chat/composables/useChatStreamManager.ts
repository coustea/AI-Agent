// src/composables/useChatStreamManager.ts

import { readonly, shallowRef } from 'vue'
import { createChatMessage } from '@/features/chat/api/chat'
import type { StreamChatParams } from '@/features/chat/types/chat'
import type { ChatEvent } from '@/features/chat/types/chatEvent'
import { useChatEvents } from '@/features/chat/composables/useChatEvents'

// ── Types ──────────────────────────────────────────────

export interface StreamCallbacks {
  onChunk?: (text: string) => void
  onEvent?: (event: ChatEvent) => void
  onDone?: (data: Record<string, unknown>) => void  // 修改：传递事件 data
  onError?: (error: Error) => void
}

export interface StreamState {
  sessionId: string
  userMessageId?: number
  status: 'streaming' | 'done' | 'error'
  error?: Error
  chatEvents: ReturnType<typeof useChatEvents>
  callbacks: StreamCallbacks
  completedAt?: number
}

// ── Global singleton state ─────────────────────────────

// 全局活跃流 Map（sessionId → StreamState）
const activeStreams = shallowRef(new Map<string, StreamState>())

const CLEANUP_DELAY_MS = 5 * 60 * 1000 // 5 minutes

// 延迟清理已完成/出错的流（5分钟后自动回收）
function scheduleCleanup(sessionId: string) {
  setTimeout(() => {
    const state = activeStreams.value.get(sessionId)
    if (state && state.status !== 'streaming') {
      activeStreams.value.delete(sessionId)
    }
  }, CLEANUP_DELAY_MS)
}

// ── Composable ─────────────────────────────────────────

// 流式消息管理器：处理创建消息→连接 SSE→回调分发全流程
export function useChatStreamManager() {
  // 启动新的流式请求并挂载事件回调
  const startStream = async (
    sessionId: string,
    params: StreamChatParams,
    callbacks: StreamCallbacks,
  ) => {
    stopStream(sessionId)

    const state: StreamState = {
      sessionId,
      status: 'streaming',
      callbacks,
      chatEvents: useChatEvents(),
    }

    activeStreams.value.set(sessionId, state)
    try {
      const response = await createChatMessage(params)
      const userMessageId = response.data.data.message_id
      state.userMessageId = userMessageId
      state.chatEvents.connect(sessionId, userMessageId, {
        onContentDelta: (chunk) => {
          state.callbacks.onChunk?.(chunk)
        },
        onEvent: (event) => {
          state.callbacks.onEvent?.(event)
        },
        onCompleted: (event) => {
          state.status = 'done'
          state.completedAt = Date.now()
          state.callbacks.onDone?.(event.data || {})  // 传递事件 data
          scheduleCleanup(sessionId)
        },
        onFailed: (error) => {
          state.status = 'error'
          state.error = error
          state.callbacks.onError?.(error)
          scheduleCleanup(sessionId)
        },
        onConnectionError: (_, willRetry) => {
          if (willRetry || state.status !== 'streaming') return
          const error = new Error('智能辅导实时连接中断')
          state.status = 'error'
          state.error = error
          state.callbacks.onError?.(error)
          scheduleCleanup(sessionId)
        },
      })
    } catch (cause) {
      const error = cause instanceof Error ? cause : new Error('智能辅导运行创建失败')
      state.status = 'error'
      state.error = error
      state.callbacks.onError?.(error)
      scheduleCleanup(sessionId)
    }
  }

  // 主动停止指定会话的流
  const stopStream = (sessionId: string) => {
    const state = activeStreams.value.get(sessionId)
    if (state) {
      state.chatEvents.close()
      activeStreams.value.delete(sessionId)
    }
  }

  // 获取指定会话的流状态
  const getStreamState = (sessionId: string): StreamState | null => {
    return activeStreams.value.get(sessionId) ?? null
  }

  // 检查会话是否处于流式输出中
  const isStreamActive = (sessionId: string): boolean => {
    return activeStreams.value.get(sessionId)?.status === 'streaming'
  }

  const getBuffer = (
    sessionId: string,
  ): { text: string; events: ChatEvent[] } => {
    const state = activeStreams.value.get(sessionId)
    if (!state) return { text: '', events: [] }
    return {
      text: state.chatEvents.content.value,
      events: [...state.chatEvents.events.value],
    }
  }

  // 更新已活跃流的回调（切换页面后重新绑定 UI）
  const resubscribe = (sessionId: string, callbacks: StreamCallbacks) => {
    const state = activeStreams.value.get(sessionId)
    if (!state) return
    state.callbacks = callbacks
  }

  return {
    activeStreams: readonly(activeStreams),
    startStream,
    stopStream,
    getStreamState,
    isStreamActive,
    getBuffer,
    resubscribe,
  }
}
