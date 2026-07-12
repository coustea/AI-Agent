// src/types/resource.ts — 资源生成相关类型定义
// 各 agent 只暴露影响生成质量的核心参数，前后端完全对齐

// 可选智能体的标识联合类型
export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'cartoon'

// 学习场景的标识联合类型
export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study' | 'path_learning'

// 单个智能体的运行时快照结构
export type ResourceAgentSnapshot = {
  agent_id: string // 智能体标识（content / mindmap / quiz …）
  event_type?: string // 最近一次事件类型
  status?: string | null // 智能体当前状态：pending / running / completed / failed
  message?: string | null // 智能体最新进度消息
  progress?: number // 进度百分比 0–100
  phase?: string | null // 当前执行阶段（如 planning / generating / reviewing）
  elapsed_ms?: number | null // 已耗时（毫秒）
  metrics?: Record<string, any> // 运行指标（token 数、生成条数等）
  artifact_id?: string | null // 产物 ID，生成完成后有值
  timestamp?: number // 快照时间戳（毫秒）
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
    // 演示幻灯智能体的配置：四项参数只影响 PPT 大纲 LLM 内容输出
    ppt: {
      template: 'auto' | 'teaching' | 'technical' | 'case_study' | 'exam_review'
      narrative_style: 'concept' | 'case_driven' | 'problem_led' | 'review'
      density: 'concise' | 'standard' | 'detailed'
      emphasis: Array<'core_concepts' | 'cases' | 'pitfalls' | 'derivation'>
    }
    // 动画讲解智能体的配置
    cartoon: {
      depth: 'overview' | 'standard' | 'deep'
      pace: 'fast' | 'normal' | 'slow'
    }
  }
}

// 资源生成任务的整体状态结构：包含进度、各智能体快照及产物列表
// 与后端 ResourceStatusSnapshot 完全对齐
export interface ResourceTaskStatus {
  resource_id: number // 资源生成任务主键
  learning_need?: string // 用户输入的学习需求
  status?: string // 任务生命周期状态：pending / planning / generating / completed / partial_completed / failed
  selected_agents?: string[] // 参与生成的智能体 id 列表
  agent_snapshots?: Record<string, ResourceAgentSnapshot> // 各智能体实时快照，键为 agent_id
  current_message?: string // 当前阶段的汇总消息
  resources?: any[] // 已完成产物列表
  updated_at?: string | null // 任务最近更新时间
}
