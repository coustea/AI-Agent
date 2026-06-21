export type AgentModule = 'chat' | 'resource' | 'path'

export type AgentEventType =
  | 'run.started'
  | 'agent.status'
  | 'tool.status'
  | 'artifact.ready'
  | 'content.delta'
  | 'run.completed'
  | 'run.failed'

export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'

export interface AgentEvent {
  event_id: string
  run_id: string
  sequence: number
  module: AgentModule
  business_id: string
  type: AgentEventType
  status: AgentRunStatus
  activity_id: string | null
  agent_id: string | null
  title: string
  summary: string
  progress: number | null
  detail: Record<string, unknown>
  elapsed_ms: number | null
  timestamp: number
}
