import http from '@/utils/http'
import type { ApiResponse } from '@/api/auth'

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

export interface AgentInfo {
  id: string
  role: string
  desc: string
  type: string
}

export interface LearningTask {
  course: string
  gap: string
  need: string
  extra: string
  template_id?: string
  template_source_url?: string | null
  template_config_url?: string | null
}

export interface ResourceGenerateRequest {
  learning_task: LearningTask
  selected_resources?: string[] | null
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

export interface ResourceArtifact {
  success?: boolean
  type?: string
  title?: string
  content?: string
  markdown_content?: string
  agent_output?: string
  outline?: string
  file_path?: string | null
  file_url?: string | null
  fileUrl?: string | null
  path?: string | null
  questions?: Array<Record<string, unknown>>
  recommendations?: Array<Record<string, unknown>>
  full_code?: string | null
  detected_language?: string | null
  error?: string | null
  [key: string]: unknown
}

export interface ResourceWorkflowEvent {
  type: 'workflow'
  stage: string
  message: string
  meta?: {
    group_index?: number
    group_total?: number
    agents?: string[]
    execution_group?: string[] | string
    [key: string]: unknown
  }
}

export interface ResourceAgentStatusEvent {
  type: 'agent_status'
  agent: string
  status: 'queued' | 'running' | 'success' | 'failed' | 'skipped'
  message: string
  meta?: {
    stage?: string
    visible?: boolean
    dependency_only?: boolean
    skipped_reason?: string
    failure_policy?: string
    dependencies?: string[]
    dependency_failures?: string[]
    [key: string]: unknown
  }
}

export interface ResourceAgentLogEvent {
  type: 'agent_log'
  agent: string
  log: string
  meta?: {
    visible?: boolean
    dependency_only?: boolean
    [key: string]: unknown
  }
}

export interface ResourceArtifactReadyEvent {
  type: 'artifact_ready'
  agent: string
  artifact: ResourceArtifact
}

export interface ResourceBundleUpdateEvent {
  type: 'bundle_update'
  completed: number
  total: number
  core_ready: boolean
  latest_agent?: string | null
  meta?: {
    visible_completed?: number
    visible_total?: number
    [key: string]: unknown
  }
}

export interface ResourceDoneEvent {
  type: 'done'
  message: string
}

export type ResourceGenerateEvent =
  | ResourceWorkflowEvent
  | ResourceAgentStatusEvent
  | ResourceAgentLogEvent
  | ResourceArtifactReadyEvent
  | ResourceBundleUpdateEvent
  | ResourceDoneEvent

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

function withResourceFileToken(event: ResourceGenerateEvent): ResourceGenerateEvent {
  if (event.type !== 'artifact_ready') return event
  const fileUrl = event.artifact.file_url
  if (!fileUrl || !fileUrl.startsWith('/api/v1/ai/resources/')) return event

  const token = localStorage.getItem('token')
  if (!token) return event

  const separator = fileUrl.includes('?') ? '&' : '?'
  return {
    ...event,
    artifact: {
      ...event.artifact,
      file_url: `${fileUrl}${separator}token=${encodeURIComponent(token)}`,
    },
  }
}

export function generateResources(
  params: ResourceGenerateRequest,
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
      let completed = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const { frames, rest } = parseSseFrames(buffer)
        buffer = rest

        for (const frame of frames) {
          const dataLines = frame
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).replace(/^ /, ''))
          if (dataLines.length === 0) continue

          const payload = normalizeSsePayload(dataLines.join('\n'))
          if (!payload || typeof payload !== 'object') continue

          const event = withResourceFileToken(payload as ResourceGenerateEvent)
          onEvent(event)
          if (event.type === 'done') {
            completed = true
            onDone()
            return
          }
        }
      }

      const finalChunk = decoder.decode()
      if (finalChunk) {
        buffer += finalChunk
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
