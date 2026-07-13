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
  sequence: number // 事件序号，用于排序与去重
  resource_id: number // 关联的资源生成任务 id
  event: ResourceEventName // 事件名称
  agent_id: string | null // 触发事件的智能体 id，全局事件时为 null
  message: string // 事件描述消息
  progress: number | null // 整体进度百分比，无进度信息时为 null
  data: Record<string, unknown> // 事件负载数据（状态、阶段、指标等）
  timestamp: number // Unix 时间戳（毫秒）
}
