// src/features/resource/model/resource.ts — 教学资源生成数据契约模型

export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'cartoon'

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced'

export type ProgrammingLanguage = 'python' | 'cpp' | 'typescript' | 'go' | 'java'

export type CartoonVoice = 'teacher' | 'coach'

export interface ResourcePreferences {
  programming_language?: ProgrammingLanguage
  voice?: CartoonVoice
}

export type ResourceContentFormat = 'markdown' | 'json' | 'pptx' | 'mp4'

export type ResourceContent = Record<string, unknown> | unknown[] | string | null

// 统一资源生成请求体
export interface ResourceGenerationRequest {
  topic: string
  learning_goal?: string
  target_resources: ResourceAgentId[]
  difficulty: DifficultyLevel
  preferences?: ResourcePreferences
}

// 子智能体生成的单项教学产物
export interface ResourceArtifact {
  id: string
  kind: ResourceAgentId
  title: string
  file_type: string
  url?: string | null
  preview_urls?: string[]
  content?: unknown
  summary?: string
  metadata?: Record<string, unknown>
}

// 主 Agent 调度的子智能体步骤
export interface ResourceStep {
  id: string
  tool_name: string
  title: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message: string
  elapsed_ms?: number
}

// 全生命周期统一状态快照 (对齐 chat.RunState)
export interface ResourceRunState {
  run_id: string
  resource_id: number
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  phase: 'queued' | 'preparing' | 'planning' | 'generating' | 'saving' | 'completed' | 'failed' | 'cancelled'
  phase_label: string
  thought_text: string
  steps: ResourceStep[]
  artifacts: ResourceArtifact[]
  total_elapsed_ms: number
  error?: string
  summary?: string
  target_resources?: ResourceAgentId[]
  topic?: string
  learning_goal?: string
  difficulty?: DifficultyLevel
}

// 单项产物明细
export interface GeneratedResourceItem {
  id: string | number
  type: ResourceAgentId
  title: string
  format: ResourceContentFormat
  content: ResourceContent
  metadata: Record<string, unknown>
  created_at: string | null
}

// 最终资源总包
export interface GeneratedResourceBundle {
  id: string | number
  title: string
  topic?: string
  learning_goal?: string
  status: string
  created_at: string
  items: GeneratedResourceItem[]
  resources: GeneratedResourceItem[]
}

// 历史列表项
export interface GeneratedResourceHistoryItem {
  id: number
  topic: string
  learning_goal?: string
  status: string
  created_at: string
  resource_count: number
  resource_types: string[]
}
