// Chat 模块独立实时事件类型定义
// 与 Resource、Path 模块完全隔离，不共享任何类型

export type ChatEventName =
  | 'run.started'
  | 'thinking'
  | 'tool.running'
  | 'tool.completed'
  | 'tool.failed'
  | 'attachment.running'
  | 'attachment.completed'
  | 'attachment.failed'
  | 'content.delta'
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