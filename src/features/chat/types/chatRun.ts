// SSE、历史和状态查询共用的完整运行快照，与后端 schemas.py 对齐

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'

export type RunPhase =
  | 'queued'
  | 'preparing'
  | 'waiting_model'
  | 'saving'
  | 'cancelling'
  | 'tool_calling'
  | 'streaming'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'interrupted'

export type StepStatus = 'running' | 'completed' | 'failed' | 'cancelled'

export type RunConnection = 'connecting' | 'connected' | 'reconnecting' | 'closed'

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
  timestamp: number
}

export interface RunStep {
  step_id: string
  title: string
  subtitle: string
  status: StepStatus
  tool_name: string
  input_preview: string
  output_preview: string
  error: string
  started_at: number
  elapsed_ms: number
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

export const isRunActive = (state: RunState): boolean =>
  state.status === 'queued' || state.status === 'running'

export const emptyRun = (run_id: string): RunState => ({
  run_id,
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
