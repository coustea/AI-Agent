import http from '@/utils/http'

// ==========================================
// 类型定义
// ==========================================

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
  diagram: Record<string, unknown> | null
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
  image_urls?: string[]
  file_urls?: string[]
  need_diagram?: boolean
  generate_video?: boolean
  enable_search?: boolean
  enable_long_term_memory?: boolean
}

export interface StreamChatEvent {
  event: string
  data: unknown
}

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

export function updateSessionTitle(sessionId: string, title: string) {
  const formData = new FormData()
  formData.append('title', title)
  return http.patch<{ code: number; message: string }>(`/ai/chat/sessions/${sessionId}`, formData)
}

// ==========================================
// 文件上传 API
// ==========================================

export function uploadFile(file: File, sessionId: string) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('session_id', sessionId)
  return http.post<{ code: number; message: string; data: UploadResult }>('/ai/chat/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
}

// ==========================================
// 图解 PNG 上传 API
// ==========================================

export function uploadDiagramImage(file: Blob, sessionId: string, messageId?: number) {
  const formData = new FormData()
  formData.append('file', file, `diagram-${Date.now()}.png`)
  formData.append('session_id', sessionId)
  if (messageId != null) {
    formData.append('message_id', String(messageId))
  }
  return http.post<{ code: number; message: string; data: UploadResult }>(
    '/ai/chat/diagram/upload',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    }
  )
}

// ==========================================
// SSE 流式聊天
// ==========================================

function normalizeSsePayload(payload: string): unknown {
  const trimmed = payload.trim()
  if (!trimmed) return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return payload
  }
}

function parseSseFrames(raw: string): { frames: string[]; rest: string } {
  const normalized = raw.replace(/\r\n/g, '\n')
  const parts = normalized.split('\n\n')
  const rest = parts.pop() || ''
  return { frames: parts, rest }
}

export function streamChat(
  params: StreamChatParams,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
  onEvent?: (event: StreamChatEvent) => void,
): AbortController {
  const controller = new AbortController()
  const token = localStorage.getItem('token')

  const formData = new FormData()
  formData.append('message', params.message)
  if (params.session_id) {
    formData.append('session_id', params.session_id)
  }
  if (params.image_urls && params.image_urls.length > 0) {
    formData.append('image_urls', params.image_urls.join(','))
  }
  if (params.file_urls && params.file_urls.length > 0) {
    formData.append('file_urls', params.file_urls.join(','))
  }
  if (params.need_diagram != null) {
    formData.append('need_diagram', String(Boolean(params.need_diagram)))
  }
  if (params.generate_video != null) {
    formData.append('generate_video', String(Boolean(params.generate_video)))
  }
  if (params.enable_search != null) {
    formData.append('enable_search', String(Boolean(params.enable_search)))
  }
  if (params.enable_long_term_memory != null) {
    formData.append('enable_long_term_memory', String(Boolean(params.enable_long_term_memory)))
  }

  fetch('/api/v1/ai/chat/stream', {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
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
      let completed = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const { frames, rest } = parseSseFrames(buffer)
        buffer = rest

        for (const frame of frames) {
          if (!frame.trim()) continue

          let eventName = 'message'
          const dataLines: string[] = []

          frame.split('\n').forEach((line) => {
            if (line.startsWith('event:')) {
              eventName = line.slice(6).trim() || 'message'
              return
            }
            if (line.startsWith('data:')) {
              dataLines.push(line.slice(5).replace(/^ /, ''))
            }
          })

          const payloadRaw = dataLines.join('\n')
          const payload = normalizeSsePayload(payloadRaw)

          if (eventName === 'token') {
            if (typeof payload === 'string') {
              onChunk(payload)
            } else {
              onChunk(JSON.stringify(payload))
            }
            continue
          }

          onEvent?.({ event: eventName, data: payload })

          if (eventName === 'error') {
            const msg = typeof payload === 'string' ? payload : JSON.stringify(payload)
            throw new Error(msg || 'stream error')
          }

          if (eventName === 'done') {
            completed = true
            onDone()
            return
          }
        }
      }

      if (!completed) {
        onDone()
      }
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError(err)
    })

  return controller
}
