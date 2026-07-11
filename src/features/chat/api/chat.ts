import http from '@/shared/api/http' // 导入配置好的 axios 实例
import type { ApiResponse } from '@/shared/api/http' // 导入响应信封类型
import type {
  ChatMessageItem,
  ChatSession,
  TeachingDiagramImage,
  UploadResult,
  StreamChatParams,
} from '@/features/chat/types/chat' // 导入聊天 DTO 类型

// ==========================================
// 聊天历史 API
// ==========================================

// 获取聊天历史消息列表
export function getChatHistory(sessionId?: string, limit = 50) {
  return http.get<ApiResponse<ChatMessageItem[]>>('/ai/chat/history', {
    params: { session_id: sessionId, limit }
  })
}

// ==========================================
// 会话管理 API
// ==========================================

// 获取会话列表
export function getSessions(limit = 20) {
  return http.get<ApiResponse<ChatSession[]>>('/ai/chat/sessions', {
    params: { limit }
  })
}

// 创建新会话
export function createSession() {
  return http.post<ApiResponse<{ id: string; title: string }>>('/ai/chat/sessions')
}

// 删除会话
export function deleteSession(sessionId: string) {
  return http.delete<ApiResponse>(`/ai/chat/sessions/${sessionId}`)
}

// 更新会话标题
export function updateSessionTitle(sessionId: string, title: string) {
  return http.patch<ApiResponse>(`/ai/chat/sessions/${sessionId}`, { title })
}

// ==========================================
// 文件上传 API
// ==========================================

// 上传附件到指定会话
export function uploadFile(file: File, sessionId: string) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('session_id', sessionId)
  return http.post<ApiResponse<UploadResult>>('/ai/chat/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }, // 文件上传编码
    timeout: 30000, // 文件上传超时 30 秒
  })
}

// ==========================================
// 保存用户消息并开始生成回答（触发后端 SSE 流）
// ==========================================

// 创建聊天消息，启动 SSE 流式回答
export function createChatMessage(params: StreamChatParams) {
  const formData = new FormData()
  if (params.message) {
    formData.append('user_input', params.message) // 用户输入文本
  }
  if (params.session_id) {
    formData.append('session_id', params.session_id) // 会话 ID
  }
  if (params.attachments && params.attachments.length > 0) {
    formData.append('attachments', JSON.stringify(params.attachments))
  }
  // 是否需要教学图解
  if (params.need_teaching_diagram != null) {
    formData.append('need_teaching_diagram', String(Boolean(params.need_teaching_diagram))) // 是否需要教学图
  }
  // 是否启用网络搜索增强
  if (params.enable_web_search != null) {
    formData.append('enable_web_search', String(Boolean(params.enable_web_search))) // 是否启用网络搜索
  }

  return http.post<ApiResponse<{ message_id: number; session_id: string }>>(
    '/ai/chat/messages',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' }, // FormData 编码
    },
  )
}

export function retryDiagramImage(messageId: number) {
  return http.post<ApiResponse<{ diagram: TeachingDiagramImage }>>(
    `/ai/chat/messages/${messageId}/diagram-image/retry`,
  )
}
