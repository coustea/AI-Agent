// Chat 模块独立实时事件类型定义
// 与 Resource、Path 模块完全隔离，不共享任何类型

export type ChatEventName =
  | 'message.started'
  | 'activity.running'
  | 'activity.completed'
  | 'activity.failed'
  | 'content.delta'
  | 'content.replace'
  | 'diagram.ready'
  | 'message.completed'
  | 'message.failed'

export interface ChatEvent {
  sequence: number
  user_message_id: number
  session_id: string
  event: ChatEventName
  message: string
  data: Record<string, unknown>
  timestamp: number
}
