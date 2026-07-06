import type { LearningScenario, ResourceGenerationRequest } from './resource'
import { getArtifactLabel } from '@/shared/content/kind'
import {
  PhCpu as Cpu,
  PhFileText as Document,
  PhShareNetwork as Share,
  PhNotePencil as Edit,
  PhBooks as Collection,
  PhGraduationCap as DataBoard,
  PhFilmStrip as FilmStrip,
  PhVideoCamera as VideoCamera,
} from '@phosphor-icons/vue'

export const PPT_AGENT_ID = 'ppt'
export const CARTOON_AGENT_ID = 'cartoon'
export const VIDEO_AGENT_ID = 'video'
export const COORDINATOR_AGENT_ID = 'coordinator'
export const BUNDLE_AGENT_ID = 'bundle'
export const SYSTEM_AGENT_IDS = ['planning', COORDINATOR_AGENT_ID, BUNDLE_AGENT_ID]
export const MIN_AGENTS = 3

export const AGENT_DISPLAY: Record<string, { label: string; icon: string }> = {
  planning: { label: '认知架构', icon: '🎯' },
  coordinator: { label: '协同中枢', icon: '⚙️' },
  content: { label: '课程讲解', icon: '📝' },
  mindmap: { label: '思维导图', icon: '🧠' },
  quiz: { label: '随堂练习', icon: '📋' },
  code: { label: '代码实操', icon: '💻' },
  reading: { label: '拓展阅读', icon: '📚' },
  ppt: { label: '演示幻灯', icon: '📊' },
  cartoon: { label: '动画讲解', icon: '🎬' },
  video: { label: '讲解视频', icon: '🎥' },
  bundle: { label: '汇编归档', icon: '📦' },
}

export const agentMetaList = [
  { id: 'content', name: '课程讲解', icon: Document, colorClass: 'text-blue' },
  { id: 'mindmap', name: '思维导图', icon: Share, colorClass: 'text-purple' },
  { id: 'code', name: '代码实操', icon: Cpu, colorClass: 'text-red' },
  { id: 'quiz', name: '随堂练习', icon: Edit, colorClass: 'text-emerald' },
  { id: 'reading', name: '拓展阅读', icon: Collection, colorClass: 'text-indigo' },
  { id: 'ppt', name: '演示幻灯', icon: DataBoard, colorClass: 'text-pink' },
  { id: 'cartoon', name: '动画讲解', icon: FilmStrip, colorClass: 'text-cyan-600' },
  { id: 'video', name: '讲解视频', icon: VideoCamera, colorClass: 'text-orange' },
]

export const getAgentMeta = (id: string) =>
  agentMetaList.find(a => a.id === id) || { name: id, icon: Document, colorClass: 'text-blue' }

export type AnyAgentConfigs = ResourceGenerationRequest['agent_configs']

export const SCENARIO_DEFAULTS: Record<string, Partial<AnyAgentConfigs>> = {
  exam_prep: {
    content: { structure: 'exam_points', depth_level: 'standard', focus_mode: 'weak_points', include_examples: true },
    quiz: { difficulty_mode: 'exam', question_count: 5, emphasis: 'analysis', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'exam_map', max_depth: 3, leaf_detail: 'annotated', show_relations: true },
    code: { programming_language: 'python', output_style: 'challenge', focus: 'application', include_tests: true },
    reading: { coverage: 'extended', language_preference: 'chinese', max_items: 3, focus: 'textbook' },
    ppt: { template: 'auto', explanation_style: 'review', density: 'detailed', focus: ['core_concepts', 'pitfalls'] },
    cartoon: { style: 'diagram', depth: 'deep', pace: 'normal', visuals: 'detailed' },
    video: { style: 'precision_light', focus: 'concept', voice: 'teacher', aspect_ratio: '16:9' },
  },
  daily_review: {
    content: { structure: 'progressive', depth_level: 'quick', focus_mode: 'weak_points', include_examples: true },
    quiz: { difficulty_mode: 'adaptive', question_count: 5, emphasis: 'foundations', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 3, leaf_detail: 'brief_note', show_relations: true },
    code: { programming_language: 'python', output_style: 'tutorial', focus: 'syntax', include_tests: false },
    reading: { coverage: 'extended', language_preference: 'chinese', max_items: 3, focus: 'textbook' },
    ppt: { template: 'instructional-editorial', explanation_style: 'review', density: 'concise', focus: ['core_concepts', 'pitfalls'] },
    cartoon: { style: 'minimal', depth: 'overview', pace: 'fast', visuals: 'clean' },
    video: { style: 'editorial_classroom', focus: 'concept', voice: 'teacher', aspect_ratio: '16:9' },
  },
  project_practice: {
    content: { structure: 'case_driven', depth_level: 'deep', focus_mode: 'full_coverage', include_examples: true },
    quiz: { difficulty_mode: 'adaptive', question_count: 5, emphasis: 'application', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, leaf_detail: 'keyword', show_relations: false },
    code: { programming_language: 'python', output_style: 'reference', focus: 'application', include_tests: true },
    reading: { coverage: 'broad', language_preference: 'chinese', max_items: 5, focus: 'engineering' },
    ppt: { template: 'technical-atlas', explanation_style: 'case_driven', density: 'detailed', focus: ['core_concepts', 'cases', 'derivation'] },
    cartoon: { style: 'dark_tech', depth: 'deep', pace: 'slow', visuals: 'detailed' },
    video: { style: 'systems_dark', focus: 'practice', voice: 'coach', aspect_ratio: '16:9' },
  },
  self_study: {
    content: { structure: 'progressive', depth_level: 'deep', focus_mode: 'key_concepts', include_examples: true },
    quiz: { difficulty_mode: 'basic', question_count: 5, emphasis: 'foundations', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, leaf_detail: 'brief_note', show_relations: true },
    code: { programming_language: 'python', output_style: 'tutorial', focus: 'syntax', include_tests: false },
    reading: { coverage: 'extended', language_preference: 'chinese', max_items: 3, focus: 'textbook' },
    ppt: { template: 'auto', explanation_style: 'review', density: 'standard', focus: ['core_concepts', 'pitfalls'] },
    cartoon: { style: 'diagram', depth: 'standard', pace: 'normal', visuals: 'balanced' },
    video: { style: 'precision_light', focus: 'concept', voice: 'teacher', aspect_ratio: '16:9' },
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

export const getResourceTypeLabel = (type: string) => {
  const label = getArtifactLabel(type)
  return label === type ? getAgentMeta(type).name || type : label
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
    cartoon: 'tone-blue',
    video: 'tone-purple',
  }
  return toneMap[type] || 'tone-blue'
}

export const getAgentOutputFormat = (agentId: string) => {
  const formatMap: Record<string, string> = {
    content: '课程讲解文档',
    mindmap: '思维导图图片',
    code: '代码实操案例',
    quiz: '随堂练习题库',
    reading: '拓展阅读文献',
    ppt: '演示幻灯课件',
    cartoon: '动画讲解视频',
    video: '讲解视频',
  }
  return formatMap[agentId] || '学习资源'
}

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
