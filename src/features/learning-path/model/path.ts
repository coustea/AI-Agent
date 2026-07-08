export type PathResourceType = 'content' | 'mindmap' | 'code' | 'reading' | 'ppt' | 'cartoon'

export interface LearningPathStage {
  stage_id: string
  title: string
}

export interface LearningPathNode {
  id: number
  node_id: string
  stage_id: string
  title: string
  status: 'locked' | 'available' | 'in_progress' | 'remediation' | 'reinforced' | 'completed' | 'completed_with_gaps'
  priority: number
  attempt_count: number
  difficulty: string | null
  prerequisites: string[]
}

export interface PathOverview {
  id: number
  module: string
  title: string
  goal: string
  topic: string | null
  overall_progress: number
  status: string
  current_node_key: string | null
  stages: LearningPathStage[]
  nodes: LearningPathNode[]
  created_at: string
  updated_at: string
}

export interface LearningPathHistoryItem {
  id: number
  title: string
  goal: string
  topic: string | null
  overall_progress: number
  status: string
  updated_at: string
}

export interface LearningPathTutorial {
  id: number
  tutorial_type: 'primary' | 'remediation' | 'reinforced' | string
  version_no: number
  based_on_tutorial_id: number | null
  title: string
  summary: string | null
  content_markdown: string
  knowledge_points: string[]
  weak_knowledge_points: string[]
  created_at: string
}

export interface LearningPathResource {
  id: number
  resource_type: PathResourceType | string
  version_no: number
  title: string
  content_format: string
  content_text: string | null
  content_json: Record<string, unknown> | null
  summary: string | null
  status: string
  error_message: string | null
  input_data: Record<string, unknown> | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface LearningPathQuestion {
  id: number
  question_no: number
  round_no: number
  mode: string
  type: string
  question: string
  choice: Record<string, string>
  answer: string
  response: string | null
  analysis: string | null
  knowledge_points: string[]
  is_correct: boolean | null
}

export interface LearningPathWorkspace {
  path: PathOverview
  node: LearningPathNode
  current_tutorial: LearningPathTutorial | null
  tutorials: LearningPathTutorial[]
  resources: LearningPathResource[]
  current_round: number
  quiz_available: boolean
}

export interface PathQuizRound {
  node_id: number
  tutorial_id: number | null
  round_no: number
  questions: LearningPathQuestion[]
}

export interface PathQuizAnswerItem {
  question_id: number
  response: string
}

export interface PathQuizSubmitRequest {
  answers: PathQuizAnswerItem[]
}

export interface PathQuizSubmitResponse {
  node_id: number
  round_no: number
  score: number
  passed: boolean
  outcome: 'completed' | 'remediation' | 'completed_with_gaps'
  weak_knowledge_points: string[]
  next_node_id: number | null
  current_tutorial_id: number | null
}

export interface PathRequest {
  goal: string
  topic?: string
  current_knowledge?: string[]
  preferences?: Record<string, unknown>
}

export interface CreatePathResponse {
  id: number
  run_id: string
  status: string
}

interface LearningSignalSnapshot {
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
  current_node_key: string | null
  signal_snapshot: LearningSignalSnapshot
  needs_optimization: boolean
  optimization_tips: string[]
}

export interface PathResourceDetail {
  id: number
  resource_type: PathResourceType | string
  version_no: number
  title: string
  content_format: string
  content_text: string | null
  content_json: Record<string, unknown> | null
  summary: string | null
  status: string
  error_message: string | null
  input_data: Record<string, unknown> | null
  metadata: Record<string, unknown>
  created_at: string
}
