// Chat 运行状态与实时事件协议 —— 与 server/app/chat/schemas.py 一一对应

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'

export type RunPhase =
  | 'queued'
  | 'preparing'
  | 'thinking'
  | 'tool_calling'
  | 'streaming'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'interrupted'

export type StepKind =
  | 'thinking'
  | 'knowledge'
  | 'memory'
  | 'vision'
  | 'document'
  | 'code'
  | 'subagent'
  | 'tool'

export type StepStatus = 'running' | 'completed' | 'failed' | 'cancelled'

export type ChatEventName =
  | 'run.snapshot'
  | 'phase.changed'
  | 'step.upsert'
  | 'text.delta'
  | 'artifact.created'
  | 'run.finished'

export interface SourceItem {
  source: string
  title: string
  heading?: string
  url?: string
  summary?: string
  score?: number | null
}

export interface SubStep {
  id: string
  title: string
  status: StepStatus
  timestamp: number
}

export interface RunStep {
  step_id: string
  kind: StepKind
  title: string
  subtitle: string
  status: StepStatus
  tool_name: string
  input_preview: string
  output_preview: string
  error: string
  started_at: number
  elapsed_ms: number
  progress?: number | null
  sub_steps: SubStep[]
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
  phase: RunPhase
  phase_label: string
  content: string
  error: string
  total_elapsed_ms: number
  steps: RunStep[]
  artifacts: ChatArtifact[]
  sources: SourceItem[]
}

export interface ChatEvent {
  run_id: string
  sequence: number
  event: ChatEventName
  data: Record<string, unknown>
  timestamp: number
}

export const isRunActive = (state: RunState): boolean =>
  state.status === 'queued' || state.status === 'running'

export const emptyRun = (run_id: string): RunState => ({
  run_id,
  sequence: 0,
  status: 'queued',
  phase: 'queued',
  phase_label: '正在连接智能体...',
  content: '',
  error: '',
  total_elapsed_ms: 0,
  steps: [],
  artifacts: [],
  sources: [],
})

export function reduceChatEvent(state: RunState, event: ChatEvent): RunState {
  if (event.run_id !== state.run_id) return state
  const data = event.data

  if (event.event === 'run.snapshot') {
    const snap = data as unknown as Partial<RunState>
    return {
      run_id: state.run_id,
      sequence: Number(snap.sequence ?? event.sequence ?? 0),
      status: (snap.status as RunStatus) || 'queued',
      phase: (snap.phase as RunPhase) || 'queued',
      phase_label: String(snap.phase_label || '等待处理'),
      content: String(snap.content || ''),
      error: String(snap.error || ''),
      total_elapsed_ms: Number(snap.total_elapsed_ms || 0),
      steps: Array.isArray(snap.steps) ? (snap.steps as RunStep[]) : [],
      artifacts: Array.isArray(snap.artifacts) ? (snap.artifacts as ChatArtifact[]) : [],
      sources: Array.isArray(snap.sources) ? (snap.sources as SourceItem[]) : [],
    }
  }

  if (event.sequence <= state.sequence && event.event !== 'run.finished') {
    return state
  }

  const next: RunState = {
    ...state,
    sequence: Math.max(state.sequence, event.sequence),
  }

  switch (event.event) {
    case 'phase.changed': {
      const nextPhase = (data.phase as RunPhase) || next.phase
      next.phase = nextPhase
      next.phase_label = String(data.phase_label || next.phase_label)
      if (data.status) {
        next.status = data.status as RunStatus
      }
      break
    }
    case 'step.upsert': {
      const step = data as unknown as RunStep
      const idx = next.steps.findIndex(item => item.step_id === step.step_id)
      if (idx >= 0) {
        const copy = [...next.steps]
        copy[idx] = step
        next.steps = copy
      } else {
        next.steps = [...next.steps, step]
      }
      break
    }
    case 'text.delta': {
      next.content += String(data.delta || '')
      break
    }
    case 'artifact.created': {
      const artifact = data as unknown as ChatArtifact
      next.artifacts = [...next.artifacts.filter(a => a.id !== artifact.id), artifact]
      break
    }
    case 'run.finished': {
      next.status = (data.status as RunStatus) || 'completed'
      next.phase = (data.phase as RunPhase) || (next.status as RunPhase)
      next.phase_label = String(data.phase_label || '回答完成')
      if (typeof data.content === 'string' && data.content) {
        next.content = data.content
      }
      next.error = String(data.error || '')
      next.total_elapsed_ms = Number(data.total_elapsed_ms || next.total_elapsed_ms)
      if (Array.isArray(data.steps)) {
        next.steps = data.steps as RunStep[]
      }
      if (Array.isArray(data.artifacts)) {
        next.artifacts = data.artifacts as ChatArtifact[]
      }
      if (Array.isArray(data.sources)) {
        next.sources = data.sources as SourceItem[]
      }
      break
    }
  }

  return next
}
