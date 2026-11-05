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

// 聊天消息（含附件、工具调用、活动状态）
export interface ChatMessageItem {
  id?: number
  user_message_id?: number | null
  role: string
  content: ContentPart[]
  tool_calls?: Array<{ id: string; name: string; args?: Record<string, unknown> }> | null
  tool_call_id?: string | null
  attachment_analyses: Array<{
    id: string
    analysis_type: string
    status: string
    content: string
    error?: string | null
  }>
  activities: Array<{
    activity_id: string
    kind: 'agent' | 'tool' | 'attachment' | 'workflow'
    stage?: string | null
    status: 'running' | 'done' | 'failed'
    title: string
    summary?: string
    message?: string
    detail?: Record<string, unknown>
  }>
  usage_metadata?: Record<string, unknown> | null
  video?: ChatVideoArtifact | null
  created_at: string | null
}

export interface ChatVideoArtifact {
  task_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  topic: string
  title?: string
  video_url?: string
  preview_url?: string
  duration_seconds?: number
  scene_count?: number
  error?: string
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
export interface StreamChatParams {
  message?: string
  session_id?: string
  attachments?: MessageAttachmentInput[]
  diagram_mode?: 'auto' | 'required'
  video_mode?: boolean
  enable_web_search?: boolean
}
