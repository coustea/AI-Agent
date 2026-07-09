// 路径规划 SSE 事件名枚举：覆盖从 profile 加载 → 搜索 → 结构生成 → 节点就绪的完整链路
export type PathEventName =
  | 'planning.started'
  | 'profile.loaded'
  | 'search.running'
  | 'search.completed'
  | 'structure.running'
  | 'node.ready'
  | 'planning.completed'
  | 'planning.failed'

// SSE 推送的路径规划事件载荷
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

// 规划结束的终态事件集合（completed 或 failed 后停止监听）
export const PATH_TERMINAL_EVENTS: Set<PathEventName> = new Set([
  'planning.completed',
  'planning.failed',
])