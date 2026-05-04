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

export type ResourceAgentId = 'content' | 'mindmap' | 'diagram' | 'quiz' | 'reading' | 'code'

export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study'

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
    diagram: {
      diagram_type:
        | 'auto'
        | 'hierarchy'
        | 'flow'
        | 'compare'
        | 'relation'
        | 'state'
        | 'class'
        | 'block'
        | 'packet'
        | 'sequence'
        | 'activity'
        | 'component'
      visual_style: 'minimal' | 'exam'
      highlight_mode: 'weak_points' | 'key_points' | 'all'
      detail_level: 'concise' | 'standard' | 'detailed'
    }
    quiz: {
      question_count: number
      difficulty_mode: 'basic' | 'adaptive' | 'exam'
      weak_point_weight: number
      exam_style: 'school' | '考研' | '考证' | 'interview'
      include_analysis: boolean
    }
    code: {
      programming_language: 'python' | 'cpp' | 'java' | 'go' | 'javascript'
      case_type: 'basic_demo' | 'algorithm_template' | 'debug_demo'
      comment_level: 'minimal' | 'standard' | 'verbose'
      include_test: boolean
      difficulty: 'beginner' | 'intermediate' | 'advanced'
    }
    reading: {
      reading_depth: 'course_extended' | 'engineering' | 'frontier'
      max_items: number
      resource_quality: 'classic' | 'latest' | 'balanced'
      include_practice: boolean
      language_preference: 'chinese' | 'english' | 'both'
    }
  }
  output_options: {
    output_format: 'json'
  }
}

interface ResourceGenerateEvent {
  event_id: string
  task_id: string
  event_type: 'workflow' | 'agent' | 'resource' | 'review' | 'bundle' | 'error' | 'done'
  stage: 'created' | 'planning' | 'generating' | 'reviewing' | 'assembling' | 'completed' | 'failed'
  agent?: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  message: string
  progress?: number
  payload: Record<string, any>
  timestamp: string
}

export function generateResources(
  params: ResourceGenerationRequest,
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

          const event = payload as ResourceGenerateEvent
          onEvent(event)

          if (event.event_type === 'done') {
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
