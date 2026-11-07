import { ref, shallowRef } from 'vue'
import { cancelChatRun, createChatMessage, getChatRun } from '@/features/chat/api/chat'
import { getAuthToken } from '@/shared/auth/token'
import type { StreamChatParams } from '@/features/chat/types/chat'
import { emptyRun, isRunActive, reduceChatEvent, type ChatEvent, type RunState } from '@/features/chat/types/chatEvent'

export function useChatRun() {
  const state = shallowRef<RunState | null>(null)
  const reconnecting = ref(false)
  let source: EventSource | null = null
  let generation = 0

  function close() {
    generation++
    source?.close()
    source = null
    reconnecting.value = false
  }

  function connect(initial: RunState, onChange: (state: RunState) => void) {
    close()
    state.value = initial
    onChange(initial)
    if (!isRunActive(initial)) return

    const epoch = generation
    const query = new URLSearchParams()
    const token = getAuthToken()
    if (token) query.set('token', token)
    const qs = query.toString()
    const url = `/api/v1/ai/chat/runs/${initial.run_id}/events${qs ? `?${qs}` : ''}`

    source = new EventSource(url)
    const connection = source

    connection.onopen = () => {
      reconnecting.value = false
    }

    connection.addEventListener('chat.event', (raw: MessageEvent) => {
      if (epoch !== generation || !state.value) return
      const event = JSON.parse(raw.data) as ChatEvent
      state.value = reduceChatEvent(state.value, event)
      onChange(state.value)
      if (!isRunActive(state.value)) close()
    })

    connection.onerror = async () => {
      reconnecting.value = true
      if (connection.readyState !== EventSource.CLOSED) return
      try {
        const response = await getChatRun(initial.run_id)
        if (epoch === generation) connect(response.data.data, onChange)
      } catch {
        if (epoch === generation) reconnecting.value = true
      }
    }
  }

  async function start(params: StreamChatParams, onChange: (state: RunState) => void) {
    const epoch = generation
    const response = await createChatMessage(params)
    const data = response.data.data
    if (epoch === generation) connect(emptyRun(data.run_id), onChange)
    return data
  }

  async function cancel() {
    if (state.value && isRunActive(state.value)) {
      await cancelChatRun(state.value.run_id)
    }
  }

  return { state, reconnecting, start, connect, close, cancel }
}
