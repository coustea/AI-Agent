export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt'

export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study' | 'path_learning'
export type ResourceStreamEventName = 'snapshot' | 'done' | 'error' | 'heartbeat' | string

interface ResourceGenerationRequest {
  learning_need: string
  learning_scenario: LearningScenario
  selected_agents: {
    agent_id: ResourceAgentId
    enabled: boolean
    priority: number
  }[]
  agent_configs: {
    content: {
      structure: 'progressive' | 'summary_first' | 'exam_points' | 'case_driven'
      include_common_mistakes: boolean
      include_examples: boolean
      focus_mode: 'weak_points' | 'key_concepts' | 'full_coverage'
      depth_level: 'quick' | 'standard' | 'deep'
    }
    mindmap: {
      map_type: 'knowledge_tree' | 'exam_map' | 'comparison_map'
      max_depth: number
      highlight_weak: boolean
      expand_weak_points: boolean
      include_prerequisites: boolean
    }
    quiz: {
      question_count: number
      difficulty_mode: 'basic' | 'adaptive' | 'exam'
      weak_point_weight: number
      exam_style: 'school' | '考研' | '考证' | 'interview'
      include_analysis: boolean
      question_types: ('single' | 'multiple' | 'judge' | 'fill')[]
    }
    code: {
      programming_language: 'python' | 'c' | 'cpp' | 'java' | 'go' | 'javascript' | 'typescript'
      case_type: 'basic_demo' | 'algorithm_template' | 'debug_demo'
      difficulty: 'beginner' | 'intermediate' | 'advanced'
    }
    reading: {
      reading_depth: 'course_extended' | 'engineering' | 'frontier'
      max_items: number
      language_preference: 'chinese' | 'english' | 'both'
    }
    ppt: {
      page_count: number
      difficulty: 'beginner' | 'intermediate' | 'advanced'
      output_format: 'preview'
    }
  }
}

export interface ResourceProgressNode {
  status: 'waiting' | 'running' | 'success' | 'failed' | 'skipped'
  progress: number
  message: string
  steps: string[]
}

export interface ResourceWorkflowProgress {
  stage: string
  progress: number
  latest_message: string
  agents: Record<string, ResourceProgressNode>
}

export interface ResourceTaskStatus {
  resource_id: number
  status: 'pending' | 'planning' | 'generating' | 'reviewing' | 'completed' | 'partial_completed' | 'failed'
  progress: ResourceWorkflowProgress
  resources?: any[]
}

export interface ResourceStreamEvent {
  event: ResourceStreamEventName
  data: unknown
}

export async function startResourceGeneration(
  params: ResourceGenerationRequest
): Promise<{ resource_id: number; status: string }> {
  const token = localStorage.getItem('token')
  const response = await fetch('/api/v1/ai/resources', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }

  const json = await response.json()
  if (json.code !== 200) {
    throw new Error(json.message || '启动生成任务失败')
  }
  return json.data
}

export async function pollResourceStatus(
  resourceId: number
): Promise<ResourceTaskStatus> {
  const token = localStorage.getItem('token')
  const response = await fetch(`/api/v1/ai/resources/${resourceId}/status`, {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }

  const json = await response.json()
  if (json.code !== 200) {
    throw new Error(json.message || '查询状态失败')
  }
  return json.data
}

export async function getResourceBundle(resourceId: number): Promise<any> {
  const token = localStorage.getItem('token')
  const response = await fetch(`/api/v1/ai/resources/${resourceId}`, {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }

  const json = await response.json()
  if (json.code !== 200) {
    throw new Error(json.message || '获取资源失败')
  }
  return json.data
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

export function streamResourceEvents(
  resourceId: number,
  onEvent: (event: ResourceStreamEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): AbortController {
  const controller = new AbortController()
  const token = localStorage.getItem('token')

  fetch(`/api/v1/ai/resources/${resourceId}/events`, {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
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

          const payload = normalizeSsePayload(dataLines.join('\n'))
          onEvent({ event: eventName, data: payload })

          if (eventName === 'error') {
            const msg = typeof payload === 'string'
              ? payload
              : (payload as any)?.message || JSON.stringify(payload)
            throw new Error(msg || 'resource stream error')
          }

          if (eventName === 'done') {
            completed = true
            onDone()
            return
          }
        }
      }

      if (!completed) onDone()
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError(err)
    })

  return controller
}
