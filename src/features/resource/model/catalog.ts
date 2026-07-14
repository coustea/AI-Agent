// 引入学习场景与资源生成请求类型，以及从共享模块获取产物类型标签
import type { LearningScenario, ResourceAgentId, ResourceGenerationRequest } from './resource'
// 引入共享的内容类型标签工具，用于根据产物类型解析展示名称
import { getArtifactLabel } from '@/shared/content/kind'
// 引入 Phosphor 图标，并为各智能体类型映射对应的图标组件
import {
  PhCpu as Cpu,
  PhFileText as Document,
  PhShareNetwork as Share,
  PhNotePencil as Edit,
  PhBooks as Collection,
  PhGraduationCap as DataBoard,
  PhFilmStrip as FilmStrip,
} from '@phosphor-icons/vue'

// PPT 智能体的固定标识
export const PPT_AGENT_ID = 'ppt'
// 动画讲解智能体的固定标识
export const CARTOON_AGENT_ID = 'cartoon'
// 协同中枢智能体的固定标识
export const COORDINATOR_AGENT_ID = 'coordinator'
// 汇编归档智能体的固定标识
export const BUNDLE_AGENT_ID = 'bundle'
// 系统级智能体列表（规划、协同中枢、汇编），用于区分用户可选与系统内部节点
export const SYSTEM_AGENT_IDS = ['planning', COORDINATOR_AGENT_ID, BUNDLE_AGENT_ID]
// 各智能体在界面上的展示信息映射：标签名称与 emoji 图标
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

// 用户可选智能体的元信息列表：名称、图标组件与主题色类
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

// 根据智能体 id 查找其元信息，找不到时回退为使用 id 作为名称的默认值
export const getAgentMeta = (id: string) =>
  agentMetaList.find(a => a.id === id) || { name: id, icon: Document, colorClass: 'text-blue' }

// 导出各智能体配置对象的联合类型，便于场景默认值复用
export type AnyAgentConfigs = ResourceGenerationRequest['agent_configs']

// 不同学习场景下的各智能体默认配置：键为场景名，值为各智能体配置的偏量
export const SCENARIO_DEFAULTS: Record<string, Partial<AnyAgentConfigs>> = {
  // 考试备考场景：强化考点、习题与分析导向
  exam_prep: {
    content: { structure: 'exam_points', depth_level: 'standard', focus_mode: 'weak_points', include_examples: true },
    quiz: { difficulty_mode: 'exam', question_count: 5, emphasis: 'analysis', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'exam_map', max_depth: 3, leaf_detail: 'annotated', show_relations: true },
    code: { programming_language: 'python', output_style: 'challenge', focus: 'application', include_tests: true },
    reading: { coverage: 'extended', language_preference: 'chinese', max_items: 3, focus: 'textbook' },
    ppt: { template: 'exam_review', narrative_style: 'review', density: 'detailed', emphasis: ['core_concepts', 'pitfalls'] },
    cartoon: { depth: 'deep', pace: 'normal' },
  },
  // 日常学习场景：循序渐进、偏基础与巩固
  daily_review: {
    content: { structure: 'progressive', depth_level: 'quick', focus_mode: 'weak_points', include_examples: true },
    quiz: { difficulty_mode: 'adaptive', question_count: 5, emphasis: 'foundations', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 3, leaf_detail: 'brief_note', show_relations: true },
    code: { programming_language: 'python', output_style: 'tutorial', focus: 'syntax', include_tests: false },
    reading: { coverage: 'extended', language_preference: 'chinese', max_items: 3, focus: 'textbook' },
    ppt: { template: 'teaching', narrative_style: 'review', density: 'concise', emphasis: ['core_concepts', 'pitfalls'] },
    cartoon: { depth: 'overview', pace: 'fast' },
  },
  // 项目实践场景：案例驱动、偏工程化与应用
  project_practice: {
    content: { structure: 'case_driven', depth_level: 'deep', focus_mode: 'full_coverage', include_examples: true },
    quiz: { difficulty_mode: 'adaptive', question_count: 5, emphasis: 'application', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, leaf_detail: 'keyword', show_relations: false },
    code: { programming_language: 'python', output_style: 'reference', focus: 'application', include_tests: true },
    reading: { coverage: 'broad', language_preference: 'chinese', max_items: 5, focus: 'engineering' },
    ppt: { template: 'technical', narrative_style: 'case_driven', density: 'detailed', emphasis: ['core_concepts', 'cases', 'derivation'] },
    cartoon: { depth: 'deep', pace: 'slow' },
  },
  // 预习自学场景：系统化、偏概念与基础架构
  self_study: {
    content: { structure: 'progressive', depth_level: 'deep', focus_mode: 'key_concepts', include_examples: true },
    quiz: { difficulty_mode: 'basic', question_count: 5, emphasis: 'foundations', question_types: ['single', 'multiple', 'judge', 'fill'] },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, leaf_detail: 'brief_note', show_relations: true },
    code: { programming_language: 'python', output_style: 'tutorial', focus: 'syntax', include_tests: false },
    reading: { coverage: 'extended', language_preference: 'chinese', max_items: 3, focus: 'textbook' },
    ppt: { template: 'teaching', narrative_style: 'concept', density: 'standard', emphasis: ['core_concepts', 'pitfalls'] },
    cartoon: { depth: 'standard', pace: 'normal' },
  },
}

// 学习场景选项列表：用于场景选择器，包含图标、名称与场景值
export const scenarioOptions: Array<{ icon: string; name: string; value: LearningScenario }> = [
  { icon: '备', name: '考试备考', value: 'exam_prep' },
  { icon: '学', name: '日常学习', value: 'daily_review' },
  { icon: '践', name: '项目实践', value: 'project_practice' },
  { icon: '预', name: '预习自学', value: 'self_study' },
  { icon: '径', name: '路径学习', value: 'path_learning' },
]

// 根据场景值返回对应的中文描述文案
export const getScenarioDesc = (scenario: string) => {
  // 场景值到描述文案的映射表
  const descMap: Record<string, string> = {
    exam_prep: '针对考试重点进行高强度强化训练',
    daily_review: '循序渐进地巩固每日所学知识点',
    project_practice: '侧重于代码实战与工程化应用能力',
    self_study: '系统化地探索新知识领域的基础架构',
    path_learning: '基于学习路径节点生成配套资源',
  }
  return descMap[scenario] || ''
}

// 根据产物/智能体类型返回展示标签：优先用共享标签，回退到智能体名称
export const getResourceTypeLabel = (type: string) => {
  const label = getArtifactLabel(type)
  return label === type ? getAgentMeta(type).name || type : label
}

// 根据产物类型返回对应的主题色类名，用于卡片着色
export const getResourceToneClass = (type: string) => {
  // 产物类型到主题色类的映射表
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


// 单个智能体事件日志的结构定义
export type AgentEventLog = {
  id: string // 事件唯一标识
  eventType?: string // 事件类型（agent.status / generation.started 等）
  phase?: string // 事件发生时智能体所处阶段
  message: string // 事件描述消息
  status?: DagNodeState['status'] // 事件关联的节点状态
  progress?: number // 事件发生时的进度百分比
  elapsedMs?: number // 事件发生时已耗时（毫秒）
  timestamp: number // 事件时间戳（毫秒）
}

// DAG 中单个智能体节点的运行时状态结构
export interface DagNodeState {
  id: string // 节点对应智能体 id
  label: string // 节点展示名称
  icon: string // 节点展示图标（emoji）
  status: 'waiting' | 'running' | 'success' | 'failed' | 'skipped' // 节点运行状态
  progress: number // 节点进度百分比 0–100
  currentMessage: string // 节点最新进度消息
  stepHistory: string[] // 历史步骤消息列表
  eventLogs: AgentEventLog[] // 事件日志列表
  isSystem: boolean // 是否为系统内部节点（规划 / 协同中枢 / 汇编）
  phase?: string // 当前执行阶段
  elapsedMs?: number // 已耗时（毫秒）
  metrics?: Record<string, any> // 运行指标
  artifactId?: string // 产物 ID
  lastUpdatedAt?: number // 最近更新时间戳（毫秒）
}

// 创建一个新的 DAG 节点，初始化为等待状态并填充展示信息
export function createDagNode(id: string, isSystem: boolean): DagNodeState {
  // 优先使用 AGENT_DISPLAY 中的展示信息，缺失时回退到类型标签
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

// 根据节点类型返回对应的图标字符串
export function getDagNodeIcon(type: string): string {
  return AGENT_DISPLAY[type]?.icon || '📄'
}
