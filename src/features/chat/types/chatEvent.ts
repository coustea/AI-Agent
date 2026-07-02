// Chat 模块独立实时事件类型定义
// 与 Resource、Path 模块完全隔离，不共享任何类型

export type ChatEventName =
  | 'run.started'
  | 'activity.running'
  | 'activity.completed'
  | 'activity.failed'
  | 'content.delta'
  | 'content.replace'
  | 'diagram.ready'
  | 'run.completed'
  | 'run.failed'

export interface ChatEvent {
  sequence: number
  run_id: string
  session_id: string
  event: ChatEventName
  message: string
  data: Record<string, unknown>
  timestamp: number
}

export const CHAT_TERMINAL_EVENTS: Set<ChatEventName> = new Set([
  'run.completed',
  'run.failed',
])
