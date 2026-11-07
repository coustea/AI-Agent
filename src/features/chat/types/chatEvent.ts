// Chat 运行事件协议 — 与 server/app/chat/harness/events.py 一一对应

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'
export type ChatEventName = 'run.started' | 'turn.started' | 'text.delta' | 'text.completed'
  | 'activity.updated' | 'artifact.created'
  | 'run.completed' | 'run.failed' | 'run.cancelled' | 'run.interrupted'

export interface ChatActivity {
  activity_id: string
  kind: string
  title: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  detail: { input?: string; output?: string; error?: string }
}

export interface ChatArtifact {
  id: string
  kind: string
  title: string
  url: string
  preview_url: string | null
  metadata: Record<string, unknown>
}

export interface RunState {
  run_id: string
  sequence: number
  status: RunStatus
  content: string
  error: string
  activities: ChatActivity[]
  artifacts: ChatArtifact[]
}

export interface ChatEvent {
  run_id: string
  sequence: number
  event: ChatEventName
  data: Record<string, unknown>
  timestamp: number
}

export const isRunActive = (state: RunState) => state.status === 'queued' || state.status === 'running'

export const emptyRun = (run_id: string): RunState => ({
  run_id, sequence: 0, status: 'queued', content: '', error: '', activities: [], artifacts: [],
})

// 同一 reducer 服务首次订阅、断线补读和历史快照恢复。
export function reduceChatEvent(state: RunState, event: ChatEvent): RunState {
  if (event.run_id !== state.run_id || event.sequence <= state.sequence) return state
  const next = { ...state, sequence: event.sequence }
  const data = event.data
  switch (event.event) {
    case 'run.started': next.status = 'running'; break
    case 'turn.started': next.content = ''; break
    case 'text.delta': next.content += String(data.delta); break
    case 'text.completed': next.content = String(data.content); break
    case 'activity.updated': {
      const activity = data as unknown as ChatActivity
      next.activities = [...state.activities.filter(a => a.activity_id !== activity.activity_id), activity]
      break
    }
    case 'artifact.created': {
      const artifact = data as unknown as ChatArtifact
      next.artifacts = [...state.artifacts.filter(a => a.id !== artifact.id), artifact]
      break
    }
    case 'run.completed': case 'run.failed': case 'run.cancelled': case 'run.interrupted':
      next.status = event.event.slice(4) as RunStatus
      next.error = String(data.error || '')
      next.activities = state.activities.map(a => a.status === 'running'
        ? { ...a, status: next.status === 'cancelled' ? 'cancelled' : 'failed' } : a)
      break
  }
  return next
}
