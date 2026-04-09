import http from '@/utils/http'

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