// src/views/ResourceGenerator.vue/constants.ts — 资源生成器常量与元数据

import type { LearningScenario, ResourceGenerationRequest } from '@/features/resource/model/resource'
import {
  PhCpu as Cpu,
  PhPaperPlaneTilt as Position,
  PhFileText as Document,
  PhShareNetwork as Share,
  PhNotePencil as Edit,
  PhBooks as Collection,
  PhGraduationCap as DataBoard,
} from '@phosphor-icons/vue'

// ===================== Agent 元数据 =====================

export const PPT_AGENT_ID = 'ppt'
export const VIDEO_AGENT_ID = 'video'
export const COORDINATOR_AGENT_ID = 'coordinator'
export const BUNDLE_AGENT_ID = 'bundle'
export const SYSTEM_AGENT_IDS = ['planning', COORDINATOR_AGENT_ID, BUNDLE_AGENT_ID]
export const MIN_AGENTS = 3

export const AGENT_DISPLAY: Record<string, { label: string; icon: string }> = {
  planning: { label: '认知架构工位', icon: '🎯' },
  coordinator: { label: '协同中枢工位', icon: '⚙️' },
  content: { label: '义理智笔工位', icon: '📝' },
  mindmap: { label: '结构图解工位', icon: '🧠' },
  quiz: { label: '考工检校工位', icon: '📋' },
  code: { label: '工程实训工位', icon: '💻' },
  reading: { label: '学术博览工位', icon: '📚' },
  ppt: { label: '宣讲排版工位', icon: '📊' },
  video: { label: '微课导演工位', icon: '🎬' },
  bundle: { label: '汇编归档工位', icon: '📦' },
}

export const agentMetaList = [
  { id: 'master', name: '认知架构师', icon: Cpu, colorClass: 'text-blue' },
  { id: 'assembler', name: '汇编归档仓', icon: Position, colorClass: 'text-indigo' },
  { id: 'content', name: '义理智笔', icon: Document, colorClass: 'text-blue' },
  { id: 'mindmap', name: '结构图解师', icon: Share, colorClass: 'text-purple' },
  { id: 'code', name: '工程实训师', icon: Cpu, colorClass: 'text-red' },
  { id: 'quiz', name: '考工检校', icon: Edit, colorClass: 'text-emerald' },
  { id: 'reading', name: '学术博览', icon: Collection, colorClass: 'text-indigo' },
  { id: 'ppt', name: '宣讲排版师', icon: DataBoard, colorClass: 'text-pink' },
  { id: 'video', name: '微课导演', icon: DataBoard, colorClass: 'text-orange' },
]

export const getAgentMeta = (id: string) =>
  agentMetaList.find(a => a.id === id) || { name: id, icon: Document, colorClass: 'text-blue' }

// ===================== 场景选项与默认值 =====================

export type AnyAgentConfigs = ResourceGenerationRequest['agent_configs']

export const SCENARIO_DEFAULTS: Record<string, Partial<AnyAgentConfigs>> = {
  exam_prep: {
    content: { structure: 'exam_points', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'standard' },
    quiz: { question_count: 5, difficulty_mode: 'exam', weak_point_weight: 50, exam_style: '考研', include_analysis: true, question_types: ['single', 'multiple', 'judge'] },
    mindmap: { map_type: 'exam_map', max_depth: 3, highlight_weak: true, expand_weak_points: false, include_prerequisites: false },
    code: { programming_language: 'python', case_type: 'algorithm_template', difficulty: 'intermediate' },
    reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' },
    ppt: {},
    video: { duration_seconds: 180, scene_count: 6, style: 'lecture', voice: 'teacher', aspect_ratio: '16:9', include_captions: true, output_format: 'preview' },
  },
  daily_review: {
    content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'quick' },
    quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true, question_types: ['single', 'multiple', 'judge'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true, expand_weak_points: false, include_prerequisites: false },
    code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'beginner' },
    reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' },
    ppt: {},
    video: { duration_seconds: 180, scene_count: 6, style: 'explainer', voice: 'teacher', aspect_ratio: '16:9', include_captions: true, output_format: 'preview' },
  },
  project_practice: {
    content: { structure: 'case_driven', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'deep' },
    quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true, question_types: ['single', 'multiple', 'judge'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: false },
    code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'intermediate' },
    reading: { reading_depth: 'engineering', max_items: 5, language_preference: 'chinese' },
    ppt: {},
    video: { duration_seconds: 240, scene_count: 8, style: 'screencast', voice: 'coach', aspect_ratio: '16:9', include_captions: true, output_format: 'preview' },
  },
  self_study: {
    content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'key_concepts', depth_level: 'deep' },
    quiz: { question_count: 5, difficulty_mode: 'basic', weak_point_weight: 50, exam_style: 'school', include_analysis: true, question_types: ['single', 'multiple', 'judge'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: false },
    code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'beginner' },
    reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' },
    ppt: {},
    video: { duration_seconds: 180, scene_count: 6, style: 'explainer', voice: 'teacher', aspect_ratio: '16:9', include_captions: true, output_format: 'preview' },
  },
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
    content: '讲义精解',
    mindmap: '结构导图',
    code: '实战演练',
    quiz: '学力检校',
    reading: '学术博览',
    ppt: '演示幻灯',
    video: '音影微课',
  }
  return labelMap[type] || getAgentMeta(type).name || type
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
  if (node.status === 'waiting') return '等待协同中枢分发任务'
  if (node.status === 'success') return '该工位已提交成果'
  if (node.status === 'failed') return '工位发生执行阻塞，请在审计日志中查看详情'
  if (node.status === 'skipped') return '本次协同已越过该工位'
  return '正在研制认知成果...'
}

export function getDagNodeIcon(type: string): string {
  return AGENT_DISPLAY[type]?.icon || '📄'
}
