export interface AgentStage {
  stage_id: string
  title: string
  description: string
}

export interface CoursePathNodeDTO {
  id: number
  node_id: string
  stage_id: string
  title: string
  status: 'locked' | 'available' | 'in_progress' | 'completed' | string
  resource_status: 'not_started' | 'generating' | 'ready' | 'failed' | string
  progress: number
  priority: number
  prerequisites: string[]
  mastery_target: string | null
  estimated_minutes: number
  difficulty: string | null
  recommendation_reason: string | null
  resource_id: number | null
}

export interface CoursePathResponse {
  id: number
  module: string
  title: string
  goal: string
  overall_progress: number
  current_stage_id: string | null
  current_node_id: string | null
  eta_days: number
  confidence: number
  status: string
  stages: AgentStage[]
  nodes: CoursePathNodeDTO[]
  needs_optimization?: boolean
  optimization_tips?: string[]
  adjustment_rationale?: string[]
  strategy_report?: string | null
  created_at: string
}

export interface CoursePathSummaryResponse {
  id: number | null
  path_id: number
  status: 'pending' | 'generating' | 'completed' | 'failed' | string
  summary_markdown: string | null
  mastery_scores: Record<string, {
    score?: number
    topic?: string
    status?: string
    [key: string]: unknown
  }> | null
  weak_points: Array<{
    topic?: string
    score?: number
    suggestion?: string
    [key: string]: unknown
  }> | null
  next_suggestions: Array<{
    title?: string
    reason?: string
    [key: string]: unknown
  }> | null
  error_message: string | null
}

export interface LearningSignalSnapshot {
  average_score: number | null
  weak_topics: string[]
  preferred_resources: string[]
  negative_feedback: string[]
  completed_resource_count: number
  viewed_resource_count: number
  active_minutes: number
  recommendations: string[]
}

export interface PathLearningEvaluationResponse {
  path_id: number
  overall_progress: number
  current_stage_id: string | null
  current_node_id: string | null
  signal_snapshot: LearningSignalSnapshot
  needs_optimization: boolean
  optimization_tips: string[]
}

export interface PathPlanFeedbackRequest {
  feedback: string
  weak_points?: string[] | null
  resource_id?: number | null
  use_learning_signals?: boolean
}

export interface GenerateCoursePathParams {
  goal: string
  topic?: string
  module?: string
  current_knowledge?: string[]
  preferences?: Record<string, unknown>
}

export interface PathGenerationTaskResponse {
  task_id: number
  module: string
  goal: string
  status: 'pending' | 'preparing' | 'planning' | 'validating' | 'completed' | 'failed' | string
  progress: number
  latest_message: string
  error_message: string | null
  generated_path_id: number | null
}

export interface PathNodeResourceRequest {
  selected_agents: {
    agent_id: 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt'
    enabled: boolean
    priority: number
  }[]
  agent_configs?: Record<string, unknown>
  output_options?: { output_format: 'json' }
}
