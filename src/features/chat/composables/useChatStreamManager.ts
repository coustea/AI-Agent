// src/composables/useChatStreamManager.ts

import { readonly, shallowRef } from 'vue'
import { createChatRun } from '@/features/chat/api/chat'
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
  status: 'streaming' | 'done' | 'error'
  error?: Error
  chatEvents: ReturnType<typeof useChatEvents>
  callbacks: StreamCallbacks
  completedAt?: number
}

// ── Global singleton state ─────────────────────────────

const activeStreams = shallowRef(new Map<string, StreamState>())

const CLEANUP_DELAY_MS = 5 * 60 * 1000 // 5 minutes

function scheduleCleanup(sessionId: string) {
  setTimeout(() => {
    const state = activeStreams.value.get(sessionId)
    if (state && state.status !== 'streaming') {
      activeStreams.value.delete(sessionId)
    }
  }, CLEANUP_DELAY_MS)
}

// ── Composable ─────────────────────────────────────────

export function useChatStreamManager() {
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
      const response = await createChatRun(params)
      const runId = response.data.data.run_id
      state.chatEvents.connect(sessionId, runId, {
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

  const stopStream = (sessionId: string) => {
    const state = activeStreams.value.get(sessionId)
    if (state) {
      state.chatEvents.close()
      activeStreams.value.delete(sessionId)
    }
  }

  const getStreamState = (sessionId: string): StreamState | null => {
    return activeStreams.value.get(sessionId) ?? null
  }

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

  const resubscribe = (sessionId: string, callbacks: StreamCallbacks) => {
    const state = activeStreams.value.get(sessionId)
    if (!state) return
    state.callbacks = callbacks
  }

  const clearStream = (sessionId: string) => {
    stopStream(sessionId)
  }

  const clearAllStreams = () => {
    for (const [sid] of activeStreams.value) {
      stopStream(sid)
    }
  }

  return {
    activeStreams: readonly(activeStreams),
    startStream,
    stopStream,
    getStreamState,
    isStreamActive,
    getBuffer,
    resubscribe,
    clearStream,
    clearAllStreams,
  }
}
