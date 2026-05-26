export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt'

export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study' | 'path_learning'

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
    ppt: {
      template_id: 'theme-logic-blue'
      page_count: number
      difficulty: 'beginner' | 'intermediate' | 'advanced'
      output_format: 'preview'
    }
  }
  output_options: {
    output_format: 'json'
  }
}

export interface ResourceGenerateEvent {
  event_id: string
  task_id: string
  event_type: 'workflow' | 'planning' | 'agent_step' | 'agent' | 'resource' | 'review' | 'bundle' | 'error' | 'done' | 'layer'
  stage: string
  agent?: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  message: string
  progress?: number
  payload: Record<string, any>
  timestamp: string
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
}

export async function startResourceGeneration(
  params: ResourceGenerationRequest
): Promise<{ resource_id: number; status: string }> {
  const token = localStorage.getItem('token')
  const response = await fetch('/api/v1/ai/generate/task', {
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
  const response = await fetch(`/api/v1/ai/generate/task/${resourceId}/status`, {
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
