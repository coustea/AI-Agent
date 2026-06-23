export type ResourceEventName =
  | 'generation.started'
  | 'plan.running'
  | 'plan.completed'
  | 'agent.pending'
  | 'agent.running'
  | 'agent.completed'
  | 'agent.failed'
  | 'artifact.ready'
  | 'generation.completed'
  | 'generation.failed'

export interface ResourceEvent {
  sequence: number
  run_id: string
  resource_id: number
  event: ResourceEventName
  agent_id: string | null
  message: string
  progress: number | null
  data: Record<string, unknown>
  timestamp: number
}

export const RESOURCE_TERMINAL_EVENTS: Set<ResourceEventName> = new Set([
  'generation.completed',
  'generation.failed',
])