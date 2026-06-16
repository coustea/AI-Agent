// src/types/resource.ts — 资源生成相关类型定义

export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'video'

export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study' | 'path_learning'
type ResourceStreamEventName = 'agent' | 'done'
  | 'agent.snapshot'
  | 'agent.step'
  | 'agent.heartbeat'
  | 'agent.artifact_ready'

/** Agent 状态值 */
type AgentStatus = 'running' | 'finished' | 'failed' | 'skipped'

/** 单条 SSE 事件数据 — 与后端 AgentEvent 对齐 */
export interface ResourceStreamEvent {
  event_type: ResourceStreamEventName
  agent_id?: string | null
  status?: AgentStatus | null
  message?: string | null
  progress: number
  run_id?: string | null
  span_id?: string | null
  phase?: string | null
  elapsed_ms?: number | null
  metrics?: Record<string, any>
  dependency?: string | null
  artifact_id?: string | null
  /** done 事件专用 */
  success?: boolean | null
  timestamp: number
}

export type ResourceAgentSnapshot = Partial<ResourceStreamEvent> & {
  agent_id: string
  progress?: number
}

export interface ResourceGenerationRequest {
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
    }
    video: {
      duration_seconds: number
      scene_count: number
      style: 'explainer' | 'lecture' | 'screencast' | 'case_walkthrough'
      voice: 'teacher' | 'coach' | 'concise'
      aspect_ratio: '16:9' | '9:16' | '1:1'
    }
  }
}

export interface ResourceTaskStatus {
  resource_id: number
  status: 'pending' | 'planning' | 'generating' | 'reviewing' | 'completed' | 'partial_completed' | 'failed'
  selected_agents?: string[]
  agent_snapshots?: Record<string, ResourceAgentSnapshot>
  overall_progress?: number
  current_message?: string
  resources?: any[]
}
