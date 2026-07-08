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

// 资源生成相关的事件名称联合类型：全局任务事件与统一的智能体状态事件
export type ResourceEventName =
  | 'generation.started'
  | 'generation.completed'
  | 'generation.failed'
  | 'agent.status'

// 终态事件集合：任务完成或失败即代表整轮生成结束，用于判断是否停止监听
export const RESOURCE_TERMINAL_EVENTS: Set<ResourceEventName> = new Set([
  'generation.completed',
  'generation.failed',
])

// 单条资源事件的结构定义：携带序号、资源 id、事件名及负载数据
export interface ResourceEvent {
  sequence: number
  resource_id: number
  event: ResourceEventName
  agent_id: string | null
  message: string
  progress: number | null
  data: Record<string, unknown>
  timestamp: number
}
