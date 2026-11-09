// src/features/resource/model/resource.ts — 资源生成统一数据契约模型

export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'cartoon'

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced'

export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study' | 'path_learning'

export type ResourceLifecycleStatus = 'pending' | 'generating' | 'completed' | 'partial' | 'failed'

export type ResourceAgentRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'interrupted'

export type ResourceContentFormat = 'markdown' | 'json' | 'pptx' | 'mp4'

export type ResourceContent = Record<string, unknown> | unknown[] | string | null

// 单项子任务节点（与后端 TaskNode 对齐）
export interface TaskNode {
  task_id: string
  title: string
  resource_type: string
  task_type: 'text' | 'tool'
  tool_name?: string | null
  dependencies: string[]
  subagent_role: string
  task_prompt?: string
  status: ResourceAgentRunStatus
  progress: number
  message: string
  elapsed_ms?: number | null
  error?: string | null
}

// 规划任务图（与后端 ExecutionPlan 对齐）
export interface ExecutionPlan {
  topic: string
  learning_goal: string
  difficulty: DifficultyLevel
  overview?: string
  tasks: TaskNode[]
}

// 统一资源生成请求体
export interface ResourceGenerationRequest {
  topic: string
  learning_goal?: string
  target_resources: ResourceAgentId[]
  difficulty: DifficultyLevel
  preferences?: Record<string, unknown>
  // 兼容别名
  learning_need?: string
  selected_agents?: { agent_id: ResourceAgentId; enabled: boolean }[]
  agent_configs?: Record<string, unknown>
}

// 单项产物明细
export interface GeneratedResourceItem {
  id: string
  type: ResourceAgentId
  title: string
  format: ResourceContentFormat
  content: ResourceContent
  metadata: Record<string, unknown>
  created_at: string | null
}

// 任务快照
export interface ResourceAgentSnapshot {
  agent_id: string
  status: ResourceAgentRunStatus
  message: string
  progress: number
  phase?: string
  elapsed_ms?: number | null
  artifact_id?: string | null
  timestamp?: number | null
}

// 任务轮询状态
export interface ResourceTaskStatus {
  resource_id: number
  topic: string
  learning_need?: string
  status: ResourceLifecycleStatus
  tasks?: TaskNode[]
  selected_agents: ResourceAgentId[]
  agent_snapshots: Record<string, ResourceAgentSnapshot>
  current_message: string
  overall_progress?: number
  resources: GeneratedResourceItem[]
  plan?: ExecutionPlan | Record<string, unknown> | null
  updated_at: string | null
}

// 产物总包
export interface GeneratedResourceBundle {
  id: string
  title: string
  topic?: string
  learning_need: string
  learning_goal?: string
  selected_agents: ResourceAgentId[]
  plan: ExecutionPlan | Record<string, unknown> | null
  resources: GeneratedResourceItem[]
  status: ResourceLifecycleStatus
  created_at: string
  updated_at: string
  metadata: {
    failed_agents?: ResourceAgentId[]
    [key: string]: unknown
  }
}

// 历史列表项
export interface GeneratedResourceHistoryItem {
  id: number
  learning_need: string
  status: ResourceLifecycleStatus
  resource_types: ResourceAgentId[]
  created_at: string | null
  updated_at: string | null
}
