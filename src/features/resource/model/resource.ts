// src/types/resource.ts — 资源生成相关类型定义
// 各 agent 只暴露影响生成质量的核心参数，前后端完全对齐

// 可选智能体的标识联合类型
export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'cartoon'

export type ResourceLifecycleStatus = 'pending' | 'generating' | 'completed' | 'partial' | 'failed'

export type ResourceAgentRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'interrupted'

export type ResourceContentFormat = 'markdown' | 'json' | 'html' | 'mp4'

export type ResourceContent = Record<string, unknown> | unknown[] | string | null

export interface CartoonResourceMetadata extends Record<string, unknown> {
  agent_id: 'cartoon'
  schema_version: 'cartoon/v8'
  engine: 'hyperframes'
  has_audio: true
  quality_passed: true
  video_url: string
  preview_url: string
  captions_url: string
  duration_seconds: number
  scene_count: number
}

// 学习场景的标识联合类型
export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study' | 'path_learning'

// 单个智能体的运行时快照结构
export type ResourceAgentSnapshot = {
  agent_id: string // 智能体标识（content / mindmap / quiz …）
  status: ResourceAgentRunStatus
  message: string // 智能体最新进度消息
  progress: number // 进度百分比 0–100
  phase: string // 当前执行阶段（如 planning / generating / reviewing）
  elapsed_ms: number | null // 已耗时（毫秒）
  artifact_id: string | null // 产物 ID，生成完成后有值
  timestamp: number | null // Unix 时间戳（毫秒）
}

export interface GeneratedResourceItem {
  id: string
  type: ResourceAgentId
  title: string
  format: ResourceContentFormat
  content: ResourceContent
  metadata: Record<string, unknown>
  created_at: string | null
}

export interface GeneratedResourceBundle {
  id: string
  title: string
  learning_need: string
  selected_agents: ResourceAgentId[]
  plan: Record<string, unknown> | null
  resources: GeneratedResourceItem[]
  status: ResourceLifecycleStatus
  created_at: string
  updated_at: string
  metadata: {
    failed_agents: ResourceAgentId[]
  }
}

export interface GeneratedResourceHistoryItem {
  id: number
  learning_need: string
  status: ResourceLifecycleStatus
  resource_types: ResourceAgentId[]
  created_at: string | null
  updated_at: string | null
}

// 发起资源生成任务的请求体：包含学习需求、场景、所选智能体及其详细配置
export interface ResourceGenerationRequest {
  learning_need: string
  learning_scenario: LearningScenario
  selected_agents: {
    agent_id: ResourceAgentId
    enabled: boolean
  }[]
  agent_configs: {
    // 课程讲解智能体的配置
    content: {
      structure: 'progressive' | 'summary_first' | 'exam_points' | 'case_driven'
      depth_level: 'quick' | 'standard' | 'deep'
      focus_mode: 'weak_points' | 'key_concepts' | 'full_coverage'
      include_examples: boolean
    }
    // 思维导图智能体的配置
    mindmap: {
      map_type: 'knowledge_tree' | 'exam_map' | 'comparison_map'
      max_depth: number
      leaf_detail: 'keyword' | 'brief_note' | 'annotated'
      show_relations: boolean
    }
    // 随堂练习智能体的配置
    quiz: {
      difficulty_mode: 'basic' | 'adaptive' | 'exam'
      question_count: number
      emphasis: 'foundations' | 'application' | 'analysis'
      question_types: Array<'single' | 'multiple' | 'judge' | 'fill'>
    }
    // 代码实操智能体的配置
    code: {
      programming_language: 'python' | 'c' | 'cpp' | 'java' | 'go' | 'javascript' | 'typescript'
      output_style: 'tutorial' | 'reference' | 'challenge'
      focus: 'syntax' | 'application' | 'debugging'
      include_tests: boolean
    }
    // 拓展阅读智能体的配置
    reading: {
      coverage: 'core' | 'extended' | 'broad'
      language_preference: 'chinese' | 'english' | 'both'
      max_items: number
      focus: 'textbook' | 'engineering' | 'research'
    }
    // 演示幻灯智能体的配置：影响共享教学叙事与视觉编排智能体
    ppt: {
      narrative_style: 'concept' | 'case_driven' | 'problem_led' | 'review'
      density: 'concise' | 'standard' | 'detailed'
      emphasis: Array<'core_concepts' | 'cases' | 'pitfalls' | 'derivation'>
    }
    // 动画讲解智能体的配置
    cartoon: {
      lesson_depth: 'focused' | 'standard' | 'deep'
      visual_density: 'moderate' | 'rich' | 'intensive'
      pace: 'fast' | 'balanced' | 'calm'
      voice: 'teacher' | 'coach'
    }
  }
}

// 资源生成任务的整体状态结构：包含进度、各智能体快照及产物列表
// 与后端 ResourceStatusSnapshot 完全对齐
export interface ResourceTaskStatus {
  resource_id: number // 资源生成任务主键
  learning_need: string // 用户输入的学习需求
  status: ResourceLifecycleStatus
  selected_agents: ResourceAgentId[] // 参与生成的智能体 id 列表
  agent_snapshots: Record<string, ResourceAgentSnapshot> // 各智能体实时快照，键为 agent_id
  current_message: string // 当前阶段的汇总消息
  resources: GeneratedResourceItem[] // 已完成产物列表
  updated_at: string | null // 任务最近更新时间
}
