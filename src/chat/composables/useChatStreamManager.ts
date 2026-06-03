// src/composables/useChatStreamManager.ts

import { ref, readonly } from 'vue'
import {
  streamChat,
} from '@/chat/api/chat'
import type {
  StreamChatParams,
  StreamChatEvent,
} from '@/chat/types/chat'

// ── Types ──────────────────────────────────────────────

export interface StreamCallbacks {
  onChunk?: (text: string) => void
  onEvent?: (event: StreamChatEvent) => void
  onDone?: () => void
  onError?: (error: Error) => void
}

export interface StreamState {
  sessionId: string
  status: 'streaming' | 'done' | 'error'
  accumulatedText: string
  events: StreamChatEvent[]
  error?: Error
  abortController?: AbortController
  callbacks: StreamCallbacks
  completedAt?: number
}

// ── Global singleton state ─────────────────────────────

const activeStreams = ref(new Map<string, StreamState>())

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
  const startStream = (
    sessionId: string,
    params: StreamChatParams,
    callbacks: StreamCallbacks,
  ) => {
    stopStream(sessionId)

    const state: StreamState = {
      sessionId,
      status: 'streaming',
      accumulatedText: '',
      events: [],
      callbacks,
    }

    // CRITICAL: Pass wrappers that read from state.callbacks dynamically.
    // This allows resubscribe() to replace callbacks on a running stream —
    // the streamChat closures resolve state.callbacks at call time, not
    // at creation time.
    const controller = streamChat(
      params,
      // onChunk — 2nd positional arg
      (chunk) => {
        state.accumulatedText += chunk
        state.callbacks.onChunk?.(chunk)
      },
      // onDone — 3rd positional arg
      () => {
        state.status = 'done'
        state.completedAt = Date.now()
        state.callbacks.onDone?.()
        scheduleCleanup(sessionId)
      },
      // onError — 4th positional arg
      (err) => {
        state.status = 'error'
        state.error = err
        state.callbacks.onError?.(err)
        scheduleCleanup(sessionId)
      },
      // onEvent — 5th positional arg
      (event) => {
        state.events.push(event)
        state.callbacks.onEvent?.(event)
      },
    )

    state.abortController = controller
    activeStreams.value.set(sessionId, state)
  }

  const stopStream = (sessionId: string) => {
    const state = activeStreams.value.get(sessionId)
    if (state) {
      state.abortController?.abort()
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
  ): { text: string; events: StreamChatEvent[] } => {
    const state = activeStreams.value.get(sessionId)
    if (!state) return { text: '', events: [] }
    return {
      text: state.accumulatedText,
      events: [...state.events],
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