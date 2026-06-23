export type PathEventName =
  | 'planning.started'
  | 'profile.loaded'
  | 'search.running'
  | 'search.completed'
  | 'structure.running'
  | 'node.ready'
  | 'planning.completed'
  | 'planning.failed'

export interface PathEvent {
  sequence: number
  run_id: string
  path_id: number
  event: PathEventName
  stage: string
  message: string
  progress: number | null
  data: Record<string, unknown>
  timestamp: number
}

export const PATH_TERMINAL_EVENTS: Set<PathEventName> = new Set([
  'planning.completed',
  'planning.failed',
])