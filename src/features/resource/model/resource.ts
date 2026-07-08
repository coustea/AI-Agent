// src/types/resource.ts — 资源生成相关类型定义
// 各 agent 只暴露影响生成质量的核心参数，前后端完全对齐

// 可选智能体的标识联合类型
export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'cartoon' | 'video'

// 学习场景的标识联合类型
export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study' | 'path_learning'

// 单个智能体的运行时快照结构
export type ResourceAgentSnapshot = {
  agent_id: string
  event_type?: string
  status?: string | null
  message?: string | null
  progress?: number
  phase?: string | null
  elapsed_ms?: number | null
  metrics?: Record<string, any>
  artifact_id?: string | null
  timestamp?: number
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
    // 演示幻灯智能体的配置
    ppt: {
      template: string
      explanation_style: 'concept' | 'case_driven' | 'problem_led' | 'review'
      density: 'concise' | 'standard' | 'detailed'
      focus: Array<'core_concepts' | 'cases' | 'pitfalls' | 'derivation'>
    }
    // 动画讲解智能体的配置
    cartoon: {
      style: 'diagram' | 'minimal' | 'dark_tech' | 'chalkboard'
      depth: 'overview' | 'standard' | 'deep'
      pace: 'fast' | 'normal' | 'slow'
      visuals: 'clean' | 'balanced' | 'detailed'
    }
    // 讲解视频智能体的配置
    video: {
      style: 'precision_light' | 'systems_dark' | 'editorial_classroom'
      focus: 'concept' | 'process' | 'comparison' | 'practice'
      voice: 'teacher' | 'coach'
      aspect_ratio: '16:9' | '9:16' | '1:1'
    }
  }
}

// 资源生成任务的整体状态结构：包含进度、各智能体快照及产物列表
export interface ResourceTaskStatus {
  resource_id: number
  learning_need?: string
  status: 'pending' | 'planning' | 'generating' | 'completed' | 'partial_completed' | 'failed'
  selected_agents?: string[]
  agent_snapshots?: Record<string, ResourceAgentSnapshot>
  overall_progress?: number
  current_message?: string
  resources?: any[]
  started_at?: string | null
  updated_at?: string | null
}
