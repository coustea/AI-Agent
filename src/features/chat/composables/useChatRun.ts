import { ref } from 'vue'
import { cancelChatRun, createChatMessage } from '@/features/chat/api/chat'
import { getAuthToken } from '@/shared/auth/token'
import type { StreamChatParams } from '@/features/chat/types/chat'
import { emptyRun, isRunActive, type RunConnection, type RunState } from '@/features/chat/types/chatRun'

export function useChatRun() {
  const connection = ref<RunConnection>('closed')
  let source: EventSource | null = null
  let generation = 0

  function close() {
    generation++
    source?.close()
    source = null
    connection.value = 'closed'
  }

  function connect(initial: RunState, onChange: (state: RunState) => void) {
    close()
    onChange(initial)
    if (!isRunActive(initial)) return

    const epoch = generation
    const query = new URLSearchParams({ token: getAuthToken() || '' })
    source = new EventSource(`/api/v1/ai/chat/runs/${initial.run_id}/events?${query}`)
    const events = source
    connection.value = 'connecting'

    events.addEventListener('run.state', (raw: MessageEvent) => {
      if (epoch !== generation) return
      const snapshot = JSON.parse(raw.data) as RunState
      if (snapshot.run_id !== initial.run_id) return
      connection.value = 'connected'
      onChange(snapshot)
      if (!isRunActive(snapshot)) close()
    })

    // EventSource 自动重连；收到新快照前继续标记连接异常。
    events.onerror = () => {
      if (epoch !== generation) return
      connection.value = events.readyState === EventSource.CLOSED ? 'closed' : 'reconnecting'
    }
  }

  async function start(params: StreamChatParams, onChange: (state: RunState) => void) {
    close()
    const epoch = generation
    const response = await createChatMessage(params)
    const data = response.data.data
    if (epoch === generation) connect(emptyRun(data.run_id), onChange)
    return data
  }

  async function cancel(runId: string) {
    await cancelChatRun(runId)
  }

  return { connection, start, connect, close, cancel }
}
