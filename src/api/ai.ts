import http from '@/utils/http'
import type { ApiResponse } from '@/api/auth'

// ==========================================
// 类型定义
// ==========================================

export interface ProfileData {
  knowledge_level: string | null
  knowledge_level_score: number | null
  cognitive_style: string | null
  cognitive_style_score: number | null
  error_pattern: string | null
  error_pattern_score: number | null
  learning_goal: string | null
  learning_goal_score: number | null
  learning_history: string | null
  learning_history_score: number | null
  interest_preference: string | null
  interest_preference_score: number | null
  learning_pace: string | null
  learning_pace_score: number | null
  cognitive_level: string | null
  cognitive_level_score: number | null
  profile_summary: string | null
  updated_at: string | null
}

export interface ProfileHistoryItem {
  version: number
  knowledge_level: string | null
  knowledge_level_score: number | null
  cognitive_style: string | null
  cognitive_style_score: number | null
  error_pattern: string | null
  error_pattern_score: number | null
  learning_goal: string | null
  learning_goal_score: number | null
  learning_history: string | null
  learning_history_score: number | null
  interest_preference: string | null
  interest_preference_score: number | null
  learning_pace: string | null
  learning_pace_score: number | null
  cognitive_level: string | null
  cognitive_level_score: number | null
  profile_summary: string | null
  change_reason: string | null
  created_at: string | null
}

export interface AttachmentInfo {
  url: string
  type: string  // "image" | "document"
  name: string
}

export interface ToolCallRecord {
  tool: string
  args: Record<string, unknown> | string
  result: string
  status: string  // "success" | "error"
}

export interface ChatMessageItem {
  role: string
  content: string
  attachments: AttachmentInfo[] | null
  tool_calls: ToolCallRecord[] | null
  created_at: string | null
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
  size_bytes: number
}

export interface StreamChatParams {
  message: string
  session_id?: string
  image_url?: string
  file_urls?: string[]
}

// ==========================================
// 画像 API
// ==========================================

export function getProfile() {
  return http.get<{ code: number; message: string; data: ProfileData }>('/ai/profile')
}

export function getProfileHistory(limit = 20) {
  return http.get<{ code: number; message: string; data: ProfileHistoryItem[] }>('/ai/profile/history', {
    params: { limit }
  })
}

// ==========================================
// 聊天历史 API
// ==========================================

export function getChatHistory(sessionId?: string, limit = 50) {
  return http.get<{ code: number; message: string; data: ChatMessageItem[] }>('/ai/chat/history', {
    params: { session_id: sessionId, limit }
  })
}

// ==========================================
// 会话管理 API
// ==========================================

export function getSessions(limit = 20) {
  return http.get<{ code: number; message: string; data: ChatSession[] }>('/ai/chat/sessions', {
    params: { limit }
  })
}

export function createSession() {
  return http.post<{ code: number; message: string; data: { id: string; title: string } }>('/ai/chat/sessions')
}

export function deleteSession(sessionId: string) {
  return http.delete<{ code: number; message: string }>(`/ai/chat/sessions/${sessionId}`)
}

// ==========================================
// 文件上传 API
// ==========================================

export function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<{ code: number; message: string; data: UploadResult }>('/ai/chat/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
}

// ==========================================
// SSE 流式聊天
// ==========================================

export function streamChat(
  params: StreamChatParams,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): AbortController {
  const controller = new AbortController()
  const token = localStorage.getItem('token')

  fetch('/api/v1/ai/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        onChunk(chunk)
      }
      onDone()
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError(err)
    })

  return controller
}

// ==========================================
// 资源生成 API
// ==========================================

export interface AgentInfo {
  id: string
  role: string
  desc: string
  type: string
}

export interface ResourceHistoryItem {
  id: number
  course: string
  gap: string
  need: string
  status: string
  has_mindmap: boolean
  has_content: boolean
  has_code: boolean
  has_quiz: boolean
  has_reading: boolean
  has_ppt: boolean
  has_image: boolean
  has_video: boolean
  created_at: string
}

export interface ResourceDetail {
  id: number
  course: string
  gap: string
  need: string
  status: string
  request_extra: string | null
  plan_result: string | null
  results: Record<string, unknown>
  created_at: string
}

export interface ResourceGenerateEvent {
  type: 'workflow' | 'agent_status' | 'agent_log' | 'artifact_ready' | 'bundle_update' | 'done'
  [key: string]: unknown
}

export interface GenerateParams {
  learning_task: {
    course: string
    gap: string
    need: string
    extra: string
  }
  selected_resources?: string[]
}

export function getAgents() {
  return http.get<ApiResponse<AgentInfo[]>>('/ai/agents')
}

export function getResourceHistory(limit = 20) {
  return http.get<ApiResponse<ResourceHistoryItem[]>>('/ai/resources', {
    params: { limit },
  })
}

export function getResourceDetail(resourceId: number) {
  return http.get<ApiResponse<ResourceDetail>>(`/ai/resources/${resourceId}`)
}

export function generateResources(
  params: GenerateParams,
  onEvent: (event: ResourceGenerateEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): AbortController {
  const controller = new AbortController()
  const token = localStorage.getItem('token')

  fetch('/api/v1/ai/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('ReadableStream not supported')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6)) as ResourceGenerateEvent
              onEvent(event)
            } catch {
              // skip malformed SSE lines
            }
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError(err)
    })

  return controller
}
