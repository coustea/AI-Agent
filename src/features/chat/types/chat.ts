// Chat 业务类型定义

import type { RunState } from './chatEvent'

interface AttachmentContentMeta {
  url?: string
  file_type?: string
  original_name?: string
  mime_type?: string | null
  size_bytes?: number
}

export type ContentPart =
  | { type: 'text'; text: string }
  | ({ type: 'image_url'; image_url: { url: string; detail?: 'auto' | 'low' | 'high' } } & AttachmentContentMeta)
  | ({ type: 'file'; file: { file_id?: string; file_data?: string; filename?: string } } & AttachmentContentMeta)

export interface ChatMessageItem {
  id: number
  role: 'user' | 'assistant'
  content: ContentPart[]
  run_id?: string
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

export interface MessageAttachmentInput {
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
  message?: string
  session_id?: string
  attachments?: MessageAttachmentInput[]
  diagram_mode?: 'auto' | 'required'
  video_mode?: boolean
}
