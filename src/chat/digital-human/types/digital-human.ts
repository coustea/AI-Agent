export interface TextMessageParams {
  text: string
  need_diagram?: boolean
  session_id?: string
  history?: Array<{ role: string; content: string }>
  attachments?: string[]
  enable_search?: boolean
  generate_video?: boolean
  speech_rate?: number
}

export interface DigitalHumanCapabilities {
  session_id?: string
  history?: Array<{ role: string; content: string }>
  enable_search?: boolean
  generate_video?: boolean
}

export interface StreamExtend {
  user_sign?: string
  appid?: string
  [key: string]: unknown
}

export interface DigitalHumanCallbacks {
  onAssistantChunk?: (chunk: string) => void
  onAssistantComplete?: () => void
  onStatus?: (status: { stage?: string; message?: string }) => void
  onDiagram?: (diagram: unknown) => void
  onAsrResult?: (text: string) => void
  onError?: (msg: string) => void
  onConnectionChange?: (connected: boolean) => void
  onAvatarReady?: (ready: boolean) => void
  onVadStateChange?: (listening: boolean) => void
  onSpeechDetectedChange?: (detected: boolean) => void
  onHistoryCleared?: (data: { session_id: string; deleted_count: number }) => void
}
