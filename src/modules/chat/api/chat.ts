import http from '@/utils/http'
import type { ApiResponse } from '@/utils/http'

// ==========================================
// 类型定义
// ==========================================

export interface AttachmentInfo {
  url: string
  type: string  // "image" | "document"
  name: string
}

export type TeachingDiagramType = 'comparison' | 'flowchart' | 'sequence' | 'framework' | 'summary' | 'hierarchy'
export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced'

// ---- 1. 对比图 ----
export interface ComparisonEntity {
  name: string
  core_label: string
  short_desc: string
}

export interface ComparisonDimension {
  name: string
  left: string
  right: string
  highlight?: string | null
}

export interface VisualSummary {
  left_keyword: string
  right_keyword: string
  center_conclusion: string
}

export interface ComparisonPayload {
  left_entity: ComparisonEntity
  right_entity: ComparisonEntity
  dimensions: ComparisonDimension[]
  visual_summary: VisualSummary
}

// ---- 2. 流程图 ----
export type FlowchartNodeType = 'start' | 'process' | 'decision' | 'end' | 'danger'

export interface FlowchartNode {
  id: string
  title: string
  short_desc?: string
  type: FlowchartNodeType
}

export interface FlowchartEdge {
  from: string
  to: string
  label?: string | null
}

export interface FlowchartPayload {
  direction: 'vertical' | 'horizontal'
  nodes: FlowchartNode[]
  edges: FlowchartEdge[]
}

// ---- 3. 时序图 ----
export interface SequenceMessage {
  from: string
  to: string
  label: string
  detail?: string | null
}

export interface SequencePayload {
  actors: string[]
  messages: SequenceMessage[]
}

// ---- 4. 知识框架图 ----
export interface FrameworkModule {
  title: string
  items: string[]
}

export interface FrameworkPayload {
  center: string
  modules: FrameworkModule[]
}

// ---- 5. 总结卡片图 ----
export interface SummaryCard {
  title: string
  short_desc: string
}

export interface SummaryPayload {
  cards: SummaryCard[]
}

// ---- 6. 层级概括图 ----
export interface HierarchyBranch {
  title: string
  children: string[]
}

export interface HierarchyPayload {
  root: string
  branches: HierarchyBranch[]
}

// ---- 辅助文字 ----
export interface TeachingContent {
  core_explanation: string
  key_points: string[]
  common_mistakes?: string[]
  examples?: string[]
  summary: string
}

// ---- 顶层 TeachingDiagram ----
export type VisualContent =
  | ComparisonPayload
  | FlowchartPayload
  | SequencePayload
  | FrameworkPayload
  | SummaryPayload
  | HierarchyPayload

export interface TeachingDiagram {
  graph_type: TeachingDiagramType
  title: string
  subtitle?: string | null
  teaching_goal: string
  course?: string | null
  difficulty: DifficultyLevel
  visual_content: VisualContent
  teaching_content: TeachingContent
}

export interface KnowledgeSource {
  rank?: number
  source: string
  file_name?: string
  chunk_index?: number
  distance?: number
}

export interface ChatMessageItem {
  role: string
  content: string
  attachments: AttachmentInfo[] | null
  teaching_diagram: TeachingDiagram | null
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
  message?: string
  history?: StreamChatHistoryItem[]
  session_id?: string
  attachments?: string[]
  need_teaching_diagram?: boolean
  generate_video?: boolean
  enable_web_search?: boolean
  enable_knowledge_base?: boolean
}

export interface StreamChatHistoryItem {
  role: 'user' | 'assistant' | 'ai' | 'system'
  content: string
  attachments?: AttachmentInfo[] | null
  teaching_diagram?: TeachingDiagram | null
}

export interface StreamChatEvent {
  event: string
  data: unknown
}

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
