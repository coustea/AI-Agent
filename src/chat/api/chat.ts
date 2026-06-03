import http from '@/utils/http'
import type { ApiResponse } from '@/utils/http'
import { createSseStream } from '@/resource/api/sse'
import type {
  ChatMessageItem,
  ChatSession,
  UploadResult,
  StreamChatParams,
  StreamChatEvent,
} from '@/chat/types/chat'

// ==========================================
// 聊天历史 API
// ==========================================

export function getChatHistory(sessionId?: string, limit = 50) {
  return http.get<ApiResponse<ChatMessageItem[]>>('/ai/chat/history', {
    params: { session_id: sessionId, limit }
  })
}

// ==========================================
// 会话管理 API
// ==========================================

export function getSessions(limit = 20) {
  return http.get<ApiResponse<ChatSession[]>>('/ai/chat/sessions', {
    params: { limit }
  })
}

export function createSession() {
  return http.post<ApiResponse<{ id: string; title: string }>>('/ai/chat/sessions')
}

export function deleteSession(sessionId: string) {
  return http.delete<ApiResponse>(`/ai/chat/sessions/${sessionId}`)
}

export function updateSessionTitle(sessionId: string, title: string) {
  return http.patch<ApiResponse>(`/ai/chat/sessions/${sessionId}`, { title })
}

// ==========================================
// 文件上传 API
// ==========================================

export function uploadFile(file: File, sessionId: string) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('session_id', sessionId)
  return http.post<ApiResponse<UploadResult>>('/ai/chat/upload', formData, {
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
  onEvent?: (event: StreamChatEvent) => void,
): AbortController {
  const controller = new AbortController()

  const formData = new FormData()
  if (params.message) {
    formData.append('message', params.message)
  }
  if (params.history && params.history.length > 0) {
    formData.append('history', JSON.stringify(params.history))
  }
  if (params.session_id) {
    formData.append('session_id', params.session_id)
  }
  if (params.attachments && params.attachments.length > 0) {
    formData.append('attachments', params.attachments.join(','))
  }
  if (params.need_teaching_diagram != null) {
    formData.append('need_teaching_diagram', String(Boolean(params.need_teaching_diagram)))
  }
  if (params.generate_video != null) {
    formData.append('generate_video', String(Boolean(params.generate_video)))
  }
  if (params.enable_web_search != null) {
    formData.append('enable_web_search', String(Boolean(params.enable_web_search)))
  }
  if (params.enable_knowledge_base != null) {
    formData.append('enable_knowledge_base', String(Boolean(params.enable_knowledge_base)))
  }

  createSseStream({
    url: '/api/v1/ai/chat/stream',
    method: 'POST',
    body: formData,
    signal: controller.signal,
    onChunk,
    onEvent: (eventName, data) => {
      onEvent?.({ event: eventName, data })
    },
    onDone,
    onError,
  })

  return controller
}
