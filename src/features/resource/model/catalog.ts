import type { ResourceAgentId } from './resource'
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

export const getResourceTypeLabel = (type: string) => {
  const label = getArtifactLabel(type)
  return label === type ? getAgentMeta(type).name || type : label
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