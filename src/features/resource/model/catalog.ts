import type { LearningScenario, ResourceAgentId, ResourceGenerationRequest } from './resource'
import { getArtifactLabel } from '@/shared/content/kind'
import {
  PhCpu as Cpu,
  PhFileText as Document,
  PhShareNetwork as Share,
  PhNotePencil as Edit,
  PhBooks as Collection,
  PhGraduationCap as DataBoard,
  PhFilmStrip as FilmStrip,
} from '@phosphor-icons/vue'

export const PPT_AGENT_ID = 'ppt'
export const CARTOON_AGENT_ID = 'cartoon'
export const COORDINATOR_AGENT_ID = 'coordinator'
export const BUNDLE_AGENT_ID = 'bundle'
export const SYSTEM_AGENT_IDS = ['planning', COORDINATOR_AGENT_ID, BUNDLE_AGENT_ID]

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
] satisfies ReadonlyArray<{
  id: ResourceAgentId
  name: string
  icon: unknown
  colorClass: string
}>

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
    ppt: { narrative_style: 'review', density: 'detailed', emphasis: ['core_concepts', 'pitfalls'], include_speaker_notes: true },
    cartoon: { visual_density: 'intensive', pace: 'balanced', target_duration_seconds: 240, voice: 'teacher' },
  },
  daily_review: {
    content: { structure: 'progressive', depth_level: 'quick', focus_mode: 'weak_points', include_examples: true },
    quiz: { difficulty_mode: 'adaptive', question_count: 5, emphasis: 'foundations', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 3, leaf_detail: 'brief_note', show_relations: true },
    code: { programming_language: 'python', output_style: 'tutorial', focus: 'syntax', include_tests: false },
    reading: { coverage: 'extended', language_preference: 'chinese', max_items: 3, focus: 'textbook' },
    ppt: { narrative_style: 'review', density: 'concise', emphasis: ['core_concepts', 'pitfalls'], include_speaker_notes: true },
    cartoon: { visual_density: 'moderate', pace: 'fast', target_duration_seconds: 120, voice: 'teacher' },
  },
  project_practice: {
    content: { structure: 'case_driven', depth_level: 'deep', focus_mode: 'full_coverage', include_examples: true },
    quiz: { difficulty_mode: 'adaptive', question_count: 5, emphasis: 'application', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, leaf_detail: 'keyword', show_relations: false },
    code: { programming_language: 'python', output_style: 'reference', focus: 'application', include_tests: true },
    reading: { coverage: 'broad', language_preference: 'chinese', max_items: 5, focus: 'engineering' },
    ppt: { narrative_style: 'case_driven', density: 'detailed', emphasis: ['core_concepts', 'cases', 'derivation'], include_speaker_notes: true },
    cartoon: { visual_density: 'intensive', pace: 'calm', target_duration_seconds: 240, voice: 'coach' },
  },
  self_study: {
    content: { structure: 'progressive', depth_level: 'deep', focus_mode: 'key_concepts', include_examples: true },
    quiz: { difficulty_mode: 'basic', question_count: 5, emphasis: 'foundations', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, leaf_detail: 'brief_note', show_relations: true },
    code: { programming_language: 'python', output_style: 'tutorial', focus: 'syntax', include_tests: false },
    reading: { coverage: 'extended', language_preference: 'chinese', max_items: 3, focus: 'textbook' },
    ppt: { narrative_style: 'concept', density: 'standard', emphasis: ['core_concepts', 'pitfalls'], include_speaker_notes: true },
    cartoon: { visual_density: 'rich', pace: 'balanced', target_duration_seconds: 180, voice: 'teacher' },
  },
}

export const scenarioOptions: Array<{ icon: string; name: string; value: LearningScenario }> = [
  { icon: '备', name: '考试备考', value: 'exam_prep' },
  { icon: '学', name: '日常学习', value: 'daily_review' },
  { icon: '践', name: '项目实践', value: 'project_practice' },
  { icon: '预', name: '预习自学', value: 'self_study' },
  { icon: '径', name: '路径学习', value: 'path_learning' },
]

export const getScenarioDesc = (scenario: string) => {
  const descMap: Record<string, string> = {
    exam_prep: '针对考试重点进行高强度强化训练',
    daily_review: '循序渐进地巩固每日所学知识点',
    project_practice: '侧重于代码实战与工程化应用能力',
    self_study: '系统化地探索新知识领域的基础架构',
    path_learning: '基于学习路径节点生成配套资源',
  }
  return descMap[scenario] || ''
}

export const getResourceTypeLabel = (type: string) => {
  const label = getArtifactLabel(type)
  return label === type ? getAgentMeta(type).name || type : label
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
  }
  return toneMap[type] || 'tone-blue'
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

export function getDagNodeIcon(type: string): string {
  return AGENT_DISPLAY[type]?.icon || '📄'
}