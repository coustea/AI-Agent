// Chat 业务类型定义

import type { RunState } from './chatRun'

export type ContentPart =
  | { type: 'text'; text: string }
  | ({ type: 'image_url' | 'file' } & UploadResult)

export interface ChatMessageItem {
  id: number
  role: 'user' | 'assistant'
  content: ContentPart[]
  run?: RunState | null
  created_at: string
}

export interface ChatSession {
  id: string
  title: string
  updated_at: string
}

export interface UploadResult {
  url: string
  file_type: string
  original_name: string
  size_bytes?: number
  mime_type?: string
}

export interface ChatRunCreated {
  run_id: string
  message_id: number
  session_id: string
}

export interface StreamChatParams {
  question?: string
  session_id?: string
  attachments?: UploadResult[]
  diagram_mode?: 'auto' | 'required'
  video_mode?: boolean
}
