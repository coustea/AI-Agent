import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  ChatMessageItem,
  ChatSession,
  UploadResult,
  StreamChatParams,
} from '@/features/chat/types/chat'

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
// 保存用户消息并开始生成回答
// ==========================================

export function createChatMessage(params: StreamChatParams) {
  const formData = new FormData()
  if (params.message) {
    formData.append('user_input', params.message)
  }
  if (params.session_id) {
    formData.append('session_id', params.session_id)
  }
  if (params.attachments && params.attachments.length > 0) {
    formData.append('attachments', JSON.stringify(params.attachments))
  }
  if (params.need_teaching_diagram != null) {
    formData.append('need_teaching_diagram', String(Boolean(params.need_teaching_diagram)))
  }
  if (params.enable_web_search != null) {
    formData.append('enable_web_search', String(Boolean(params.enable_web_search)))
  }

  return http.post<ApiResponse<{ message_id: number; session_id: string }>>(
    '/ai/chat/messages',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  )
}
