// src/composables/useChatStreamManager.ts

import { readonly, shallowRef } from 'vue'
import {
  createChatRun,
} from '@/features/chat/api/chat'
import type {
  StreamChatParams,
} from '@/features/chat/model/chat'
import type { AgentEvent } from '@/shared/agent-events/model'
import { useAgentRun } from '@/shared/agent-events/useAgentRun'

// ── Types ──────────────────────────────────────────────

export interface StreamCallbacks {
  onChunk?: (text: string) => void
  onEvent?: (event: AgentEvent) => void
  onDone?: () => void
  onError?: (error: Error) => void
}

export interface StreamState {
  sessionId: string
  status: 'streaming' | 'done' | 'error'
  error?: Error
  agentRun: ReturnType<typeof useAgentRun>
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
      agentRun: useAgentRun(),
    }

    activeStreams.value.set(sessionId, state)
    try {
      const response = await createChatRun(params)
      const runId = response.data.data.run_id
      state.agentRun.connect(runId, {
        onContentDelta: (chunk) => {
          state.callbacks.onChunk?.(chunk)
        },
        onEvent: (event) => {
          state.callbacks.onEvent?.(event)
        },
        onCompleted: () => {
          state.status = 'done'
          state.completedAt = Date.now()
          state.callbacks.onDone?.()
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
      state.agentRun.close()
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
  ): { text: string; events: AgentEvent[] } => {
    const state = activeStreams.value.get(sessionId)
    if (!state) return { text: '', events: [] }
    return {
      text: state.agentRun.content.value,
      events: [...state.agentRun.events.value],
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
