export interface TextMessageParams {
  text: string
  need_diagram?: boolean
  session_id?: string
  attachments?: string[]
  enable_search?: boolean
  speech_rate?: number
}

export interface DigitalHumanCapabilities {
  session_id?: string
  enable_search?: boolean
}

export interface StreamExtend {
  user_sign?: string
  appid?: string
  [key: string]: unknown
}

// ── 数字人状态类型 ──
export type DigitalHumanStateType =
  | 'idle'
  | 'avatar_connecting'
  | 'avatar_ready'
  | 'listening'
  | 'recognizing'
  | 'thinking'
  | 'speaking'
  | 'error'

// ── WebSocket 消息类型接口 ──
export interface TurnStartMessage {
  type: 'turn_start'
  turn_id: string
}

export interface DigitalHumanStateMessage {
  type: 'digital_human_state'
  state: DigitalHumanStateType
  turn_id?: string
  message?: string
}

export interface AssistantChunkMessage {
  type: 'assistant_chunk'
  turn_id?: string
  content: string
}

export interface AssistantCompleteMessage {
  type: 'assistant_complete'
  turn_id?: string
}

export interface AvatarSpeakingMessage {
  type: 'avatar_speaking'
  turn_id?: string
  data: unknown
}

export interface AvatarStoppedMessage {
  type: 'avatar_stopped'
  turn_id?: string
  data: unknown
}

export interface DiagramMessage {
  type: 'diagram'
  turn_id?: string
  data: unknown
}

export interface StatusMessage {
  type: 'status'
  turn_id?: string
  data: { stage?: string; message?: string }
}

export interface ErrorMessage {
  type: 'error'
  turn_id?: string
  content: string
}

export interface DigitalHumanCallbacks {
  onAssistantChunk?: (chunk: string, turn_id?: string) => void
  onAssistantComplete?: (turn_id?: string) => void
  onStatus?: (status: { stage?: string; message?: string }) => void
  onDiagram?: (diagram: unknown, turn_id?: string) => void
  onAsrResult?: (text: string) => void
  onError?: (msg: string) => void
  onConnectionChange?: (connected: boolean) => void
  onAvatarReady?: (ready: boolean) => void
  onVadStateChange?: (listening: boolean) => void
  onSpeechDetectedChange?: (detected: boolean) => void
  onHistoryCleared?: (data: { session_id: string; deleted_count: number }) => void
  onDigitalHumanStateChange?: (state: DigitalHumanStateType, turn_id?: string) => void
  onThinkingStart?: () => void
  onThinkingEnd?: () => void
  onAvatarStopped?: () => void
}
