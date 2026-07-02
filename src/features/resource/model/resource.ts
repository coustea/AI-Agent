// src/types/resource.ts — 资源生成相关类型定义

export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'video'

export type LearningScenario = 'exam_prep' | 'daily_review' | 'project_practice' | 'self_study' | 'path_learning'
// PPT 配置类型定义
export type PptThemeId = 'bold-signal' | 'electric-studio' | 'creative-voltage' | 'dark-botanical' | 'notebook-tabs' | 'pastel-geometry' | 'split-pastel' | 'vintage-editorial' | 'neon-cyber' | 'terminal-green' | 'swiss-modern' | 'paper-ink'
export type PptExplanationStyle = 'conceptual' | 'procedural' | 'comparative'
export type PptVisualEmphasis = 'minimal' | 'balanced' | 'rich'

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
      question_types: Array<'single' | 'multiple' | 'judge' | 'fill'>
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
      theme_id: PptThemeId
      explanation_style: PptExplanationStyle
      visual_emphasis: PptVisualEmphasis
    }
    video: {
      duration_seconds: number
      scene_count: number
      style: 'explainer' | 'lecture' | 'screencast' | 'case_walkthrough'
      voice: 'teacher' | 'coach' | 'concise'
      aspect_ratio: '16:9' | '9:16' | '1:1'
      include_captions: boolean
      output_format: 'preview'
    }
  }
}

export interface ResourceTaskStatus {
  resource_id: number
  run_id?: string | null
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
