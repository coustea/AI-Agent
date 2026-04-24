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
  image_urls?: string[]
  file_urls?: string[]
  generate_image?: boolean
  generate_video?: boolean
  files?: File[]
}

export interface StreamChatEvent {
  event: string
  data: unknown
}

// ==========================================
// 路径规划 API
// ==========================================

export type PathNodeStatus = 'success' | 'processing' | 'wait'
export type PathStageStatus = PathNodeStatus

export interface PathNode {
  id: string
  title: string
  status: PathNodeStatus
  progress: number
  priority: number
  desc: string | null
}

export interface PathStage {
  id: string
  title: string
  status: PathStageStatus
  progress: number
  nodes: PathNode[]
}

export interface PathPlanSummary {
  overall_progress: number
  current_stage: string | null
  knowledge_level: string | null
  eta_days: number
  confidence: number
}

export interface PathPlanInsights {
  adjustment_reason: string
  next_action: string
}

export interface PathPlanMeta {
  generated_at: string
  data_sources: string[]
  resource_id: number | null
  plan_version: number
}

export interface PathPlan {
  summary: PathPlanSummary
  stages: PathStage[]
  insights: PathPlanInsights
  meta: PathPlanMeta
}

export interface PathPlanFeedbackParams {
  feedback: string
  weak_points?: string[]
  resource_id?: number | null
}

export function getPathPlan(resourceId?: number) {
  return http.get<{ code: number; message: string; data: PathPlan }>('/ai/path-plan', {
    params: resourceId ? { resource_id: resourceId } : undefined,
  })
}

export function rebuildPathPlan(resourceId?: number) {
  return http.post<{ code: number; message: string; data: PathPlan }>('/ai/path-plan/rebuild', {
    resource_id: resourceId ?? null,
  })
}

export function applyPathFeedback(params: PathPlanFeedbackParams) {
  return http.post<{ code: number; message: string; data: PathPlan }>('/ai/path-plan/feedback', params)
}

// ==========================================
// 学习效果评估 API
// ==========================================

export type LearningEventType =
  | 'resource_viewed'
  | 'resource_completed'
  | 'quiz_submitted'
  | 'path_feedback'
  | 'tutor_helpful'
  | 'resource_feedback'

export interface LearningEventCreate {
  event_type: LearningEventType
  session_id?: string | null
  resource_id?: number | null
  course?: string | null
  topic?: string | null
  score?: number | null
  duration_seconds?: number | null
  feedback?: string | null
  metadata?: Record<string, unknown>
}

export interface LearningEventItem {
  id: number
  event_type: string
  course: string | null
  topic: string | null
  score: number | null
  duration_seconds: number | null
  feedback: string | null
  created_at: string
}

export interface EvaluationMetric {
  label: string
  value: string
  trend: string
}

export interface EvaluationSummary {
  event_count: number
  average_score: number | null
  completed_resources: number
  viewed_resources: number
  active_minutes: number
  weak_topics: string[]
  preferred_resources: string[]
  recommendations: string[]
  metrics: EvaluationMetric[]
  recent_events: LearningEventItem[]
}

export function recordLearningEvent(payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/events', payload)
}

export function getEvaluationSummary(limit = 100) {
  return http.get<ApiResponse<EvaluationSummary>>('/ai/evaluation/summary', {
    params: { limit },
  })
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

export function uploadFile(file: File, sessionId: string) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('session_id', sessionId)
  return http.post<{ code: number; message: string; data: UploadResult }>('/ai/chat/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
}

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
  if (params.generate_image != null) {
    formData.append('generate_image', String(Boolean(params.generate_image)))
  }
  if (params.generate_video != null) {
    formData.append('generate_video', String(Boolean(params.generate_video)))
  }
  if (params.files && params.files.length > 0) {
    params.files.forEach((file) => formData.append('files', file))
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
