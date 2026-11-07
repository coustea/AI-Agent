// src/types/chat.ts — 聊天相关类型定义

// 附件元数据（URL、类型、名称等）
interface AttachmentContentMeta {
  url?: string
  file_type?: string
  original_name?: string
  mime_type?: string | null
  size_bytes?: number
}

export type ContentPart =
  | { type: "text"; text: string }
  | ({ type: "image_url"; image_url: { url: string; detail?: "auto" | "low" | "high" } } & AttachmentContentMeta)
  | ({ type: "file"; file: { file_id?: string; file_data?: string; filename?: string } } & AttachmentContentMeta)

export interface ChatMessageItem {
  id: number
  role: 'user' | 'assistant' | 'tool'
  content: ContentPart[]
  run_id?: string
  run?: import('./chatEvent').RunState | null
  attachment_analyses?: unknown[]
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

// SSE 流式聊天请求参数
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
