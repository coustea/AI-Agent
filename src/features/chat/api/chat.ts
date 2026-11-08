import http from '@/shared/api/http' // 导入配置好的 axios 实例
import type { ApiResponse } from '@/shared/api/http' // 导入响应信封类型
import type {
  ChatMessageItem,
  ChatRunCreated,
  ChatSession,
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
  return http.post<ApiResponse<ChatRunCreated>>('/ai/chat/messages', params)
}


// 请求取消一次运行
export function cancelChatRun(runId: string) {
  return http.post<ApiResponse<{ run_id: string; status: string }>>(`/ai/chat/runs/${runId}/cancel`)
}
