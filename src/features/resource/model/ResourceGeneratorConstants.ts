// src/views/ResourceGenerator.vue/constants.ts — 资源生成器常量与元数据

import type { LearningScenario } from '@/features/resource/model/resource'
import {
  Cpu, CircleCheckFilled, Position,
  Document, Share, Edit, Collection, DataBoard,
} from '@element-plus/icons-vue'

// ===================== Agent 元数据 =====================

export const PPT_AGENT_ID = 'ppt'
const VIDEO_AGENT_ID = 'video'
export const PRE_REVIEW_AGENT_ID = 'pre_review'
export const PPT_REVIEW_AGENT_ID = 'ppt_review'
const VIDEO_REVIEW_AGENT_ID = 'video_review'
export const COORDINATOR_AGENT_ID = 'coordinator'
export const BUNDLE_AGENT_ID = 'bundle'
export const SYSTEM_AGENT_IDS = ['planning', COORDINATOR_AGENT_ID, PRE_REVIEW_AGENT_ID, PPT_REVIEW_AGENT_ID, VIDEO_REVIEW_AGENT_ID, 'review', BUNDLE_AGENT_ID]
export const MIN_AGENTS = 3

export const AGENT_DISPLAY: Record<string, { label: string; icon: string }> = {
  planning: { label: '规划任务', icon: '🎯' },
  coordinator: { label: '并行调度中枢', icon: '⚙️' },
  content: { label: '讲义生成助手', icon: '📝' },
  mindmap: { label: '导图绘制助手', icon: '🧠' },
  quiz: { label: '自测题生成助手', icon: '📋' },
  code: { label: '实战演练助手', icon: '💻' },
  reading: { label: '拓展阅读助手', icon: '📚' },
  ppt: { label: '演示文稿助手', icon: '📊' },
  video: { label: '讲解视频助手', icon: '🎬' },
  pre_review: { label: '前置安全审核', icon: '🛡️' },
  ppt_review: { label: 'PPT 安全审核', icon: '🔍' },
  video_review: { label: '视频安全审核', icon: '🔍' },
  review: { label: '质量把关助手', icon: '🔍' },
  bundle: { label: '资源打包助手', icon: '📦' },
}

export const agentMetaList = [
  { id: 'master', name: '规划中枢', icon: Cpu, colorClass: 'text-blue' },
  { id: 'reviewer', name: '质量把关助手', icon: CircleCheckFilled, colorClass: 'text-emerald' },
  { id: 'assembler', name: '资源打包助手', icon: Position, colorClass: 'text-indigo' },
  { id: 'content', name: '讲义生成助手', icon: Document, colorClass: 'text-blue' },
  { id: 'mindmap', name: '导图绘制助手', icon: Share, colorClass: 'text-purple' },
  { id: 'code', name: '实战演练助手', icon: Cpu, colorClass: 'text-red' },
  { id: 'quiz', name: '自测题生成助手', icon: Edit, colorClass: 'text-emerald' },
  { id: 'reading', name: '拓展阅读助手', icon: Collection, colorClass: 'text-indigo' },
  { id: 'ppt', name: '演示文稿助手', icon: DataBoard, colorClass: 'text-pink' },
  { id: 'video', name: '讲解视频助手', icon: DataBoard, colorClass: 'text-orange' },
]

export const getAgentMeta = (id: string) =>
  agentMetaList.find(a => a.id === id) || { name: id, icon: Document, colorClass: 'text-blue' }

// ===================== 场景选项与默认值 =====================

export type QuizQuestionType = 'single' | 'multiple' | 'judge' | 'fill'

export type AnyAgentConfigs = {
  content: { structure: string; include_common_mistakes: boolean; include_examples: boolean; focus_mode: string; depth_level: string }
  mindmap: { map_type: string; max_depth: number; highlight_weak: boolean; expand_weak_points: boolean; include_prerequisites: boolean }
  quiz: { question_count: number; difficulty_mode: string; weak_point_weight: number; exam_style: string; include_analysis: boolean; question_types?: QuizQuestionType[] }
  code: { programming_language: string; case_type: string; difficulty: string }
  reading: { reading_depth: string; max_items: number; language_preference: string }
  ppt: { page_count: number; difficulty: string; output_format: string }
  video: { duration_seconds: number; scene_count: number; style: string; voice: string; aspect_ratio: string }
}

export const SCENARIO_DEFAULTS: Record<string, Partial<AnyAgentConfigs>> = {
  exam_prep: { content: { structure: 'exam_points', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'standard' }, quiz: { question_count: 5, difficulty_mode: 'exam', weak_point_weight: 70, exam_style: '考研', include_analysis: true }, mindmap: { map_type: 'exam_map', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false }, code: { programming_language: 'python', case_type: 'algorithm_template', difficulty: 'intermediate' }, reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' }, ppt: { page_count: 8, difficulty: 'advanced', output_format: 'preview' }, video: { duration_seconds: 180, scene_count: 6, style: 'lecture', voice: 'teacher', aspect_ratio: '16:9' } },
  daily_review: { content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'quick' }, quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false }, code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'beginner' }, reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' }, ppt: { page_count: 5, difficulty: 'intermediate', output_format: 'preview' }, video: { duration_seconds: 180, scene_count: 6, style: 'explainer', voice: 'teacher', aspect_ratio: '16:9' } },
  project_practice: { content: { structure: 'case_driven', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'deep' }, quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 30, exam_style: 'school', include_analysis: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true }, code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'intermediate' }, reading: { reading_depth: 'engineering', max_items: 5, language_preference: 'chinese' }, ppt: { page_count: 10, difficulty: 'intermediate', output_format: 'preview' }, video: { duration_seconds: 240, scene_count: 8, style: 'screencast', voice: 'coach', aspect_ratio: '16:9' } },
  self_study: { content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'key_concepts', depth_level: 'deep' }, quiz: { question_count: 5, difficulty_mode: 'basic', weak_point_weight: 40, exam_style: 'school', include_analysis: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true }, code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'beginner' }, reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' }, ppt: { page_count: 6, difficulty: 'beginner', output_format: 'preview' }, video: { duration_seconds: 180, scene_count: 6, style: 'explainer', voice: 'teacher', aspect_ratio: '16:9' } },
}

export const scenarioOptions: Array<{ icon: string; name: string; value: LearningScenario }> = [
  { icon: '备', name: '考试备考', value: 'exam_prep' },
  { icon: '学', name: '日常学习', value: 'daily_review' },
  { icon: '践', name: '项目实践', value: 'project_practice' },
  { icon: '预', name: '预习自学', value: 'self_study' },
]

export const getScenarioDesc = (scenario: string) => {
  const descMap: Record<string, string> = {
    exam_prep: '针对考试重点进行高强度强化训练',
    daily_review: '循序渐进地巩固每日所学知识点',
    project_practice: '侧重于代码实战与工程化应用能力',
    self_study: '系统化地探索新知识领域的基础架构',
  }
  return descMap[scenario] || ''
}

// ===================== 资源展示辅助 =====================

export const getResourceTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = {
    content: '专业讲解',
    mindmap: '知识导图',
    code: '代码案例',
    quiz: '自测题',
    reading: '拓展阅读',
    ppt: '演示文稿',
    video: '讲解视频',
    reviewer: '质量审查',
  }
  return labelMap[type] || getAgentMeta(type).name || type
}

export const getResourceUsageHint = (type: string) => {
  const hintMap: Record<string, string> = {
    content: '先阅读讲解，建立基础概念和关键术语理解。',
    mindmap: '用于梳理知识层级、概念关系和复习框架。',
    code: '通过代码案例把知识点落到实践，适合边运行边理解。',
    quiz: '完成自测题，检查掌握情况并定位仍然薄弱的知识点。',
    reading: '用于课后拓展和深入理解，适合完成基础资源后阅读。',
    ppt: '精美的自动生成幻灯片，可用于直接演示或快速概览。',
    video: '结构化讲解视频脚本，包含分镜旁白和视觉提示。',
  }
  return hintMap[type] || '建议结合本次学习目标使用该资源。'
}

export const getDefaultResourceFormat = (type: string) => {
  const formatMap: Record<string, string> = {
    content: 'Markdown',
    mindmap: 'Markdown / Tree',
    code: 'Code',
    quiz: 'Quiz JSON',
    reading: 'Reading List',
    ppt: 'PPT JSON',
    video: 'Video JSON',
  }
  return formatMap[type] || 'Resource'
}

export const getEstimatedTime = (type: string) => {
  const timeMap: Record<string, string> = {
    content: '10-15 分钟',
    mindmap: '5-8 分钟',
    code: '15-25 分钟',
    quiz: '10-20 分钟',
    reading: '20-30 分钟',
    ppt: '5-10 分钟',
    video: '3-5 分钟',
  }
  return timeMap[type] || '待评估'
}

export const getDifficultyLabel = (difficulty?: string) => {
  const difficultyMap: Record<string, string> = {
    basic: '基础',
    beginner: '入门',
    intermediate: '进阶',
    advanced: '提高',
    hard: '挑战',
    exam: '考试强化',
  }
  return difficultyMap[String(difficulty || '').toLowerCase()] || difficulty || '自适应'
}

export const getResourceToneClass = (type: string) => {
  const toneMap: Record<string, string> = {
    content: 'tone-blue',
    mindmap: 'tone-purple',
    code: 'tone-rose',
    quiz: 'tone-emerald',
    reading: 'tone-indigo',
    ppt: 'tone-pink',
    video: 'tone-orange',
  }
  return toneMap[type] || 'tone-blue'
}

export const getAgentOutputFormat = (agentId: string) => {
  const formatMap: Record<string, string> = {
    content: 'Markdown 讲解',
    mindmap: '知识结构图',
    code: 'Code 示例',
    quiz: 'Quiz 题库',
    reading: 'Reading List',
    ppt: 'PPT 页面',
    video: '视频脚本',
  }
  return formatMap[agentId] || '学习资源'
}

// ===================== DAG 节点类型 =====================

export type AgentEventLog = {
  id: string
  eventType?: string
  phase?: string
  message: string
  status?: DagNodeState['status']
  progress?: number
  elapsedMs?: number
  timestamp: number
}

export interface DagNodeState {
  id: string
  label: string
  icon: string
  status: 'waiting' | 'running' | 'success' | 'failed' | 'skipped'
  progress: number
  currentMessage: string
  stepHistory: string[]
  eventLogs: AgentEventLog[]
  isSystem: boolean
  phase?: string
  elapsedMs?: number
  metrics?: Record<string, any>
  artifactId?: string
  lastUpdatedAt?: number
  reviewWarning?: boolean
}

export function createDagNode(id: string, isSystem: boolean): DagNodeState {
  const display: { label: string; icon: string } = AGENT_DISPLAY[id] || { label: getResourceTypeLabel(id), icon: '📄' }
  return {
    id,
    label: display.label,
    icon: display.icon,
    status: 'waiting',
    progress: 0,
    currentMessage: '',
    stepHistory: [],
    eventLogs: [],
    isSystem,
  }
}

export function getNodeFallbackMessage(node: DagNodeState) {
  if (node.status === 'waiting') return '等待 MasterAgent 调度'
  if (node.status === 'success') return '该节点已完成处理'
  if (node.status === 'failed') return '该节点执行失败，请查看日志'
  if (node.status === 'skipped') return '本次任务未启用该节点'
  return '正在处理任务'
}

export function getDagNodeIcon(type: string): string {
  return AGENT_DISPLAY[type]?.icon || '📄'
}

export function formatBentoTitle(title: string | undefined, type: string): string {
  const fallback = getResourceTypeLabel(type)
  const raw = String(title || fallback).trim()
  if (!raw) return fallback
  const suffixPattern = /\s*[-－—]\s*(内容讲解|思维导图|代码实操案例|拓展阅读|自测题)\s*$/
  const matched = raw.match(suffixPattern)
  if (!matched) return raw
  const suffix = matched[1] || ''
  const prefix = raw.replace(suffixPattern, '').trim()
  return prefix ? `${prefix}\n- ${suffix}` : suffix
}
