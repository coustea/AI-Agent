// Resource 模块统一事件协议（方案 C）
//
// 事件名只有 4 种：
//   generation.started  — 全局：任务开始
//   generation.completed — 全局：任务完成
//   generation.failed   — 全局：任务失败
//   agent.status        — 统一：任何 agent 状态变化
//
// agent.status 的 data 中包含：
//   status: 'pending' | 'running' | 'completed' | 'failed'
//   phase?: string
//   progress?: number
//   metrics?: Record<string, unknown>
//   elapsed_ms?: number
//   artifact_id?: string

export type ResourceEventName =
  | 'generation.started'
  | 'generation.completed'
  | 'generation.failed'
  | 'agent.status'

export const RESOURCE_TERMINAL_EVENTS: Set<ResourceEventName> = new Set([
  'generation.completed',
  'generation.failed',
])

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
