import type { AgentActivity, TeachingDiagram } from '@/features/chat/model/chat'

export interface PendingFile {
  file?: File
  url?: string
  localUrl?: string
  fileType: string
  name: string
}

export interface Attachment {
  url: string
  type: string
  name: string
}

export type ContextCompressionStage = 'compression_checking' | 'compression_running' | 'compression_done'

/** Agent 工作状态 - 基于后端事件 */
export type AgentStage =
  | 'idle'           // 空闲
  | 'classifying'    // 正在分析问题
  | 'analyzing_files' // 正在分析附件
  | 'searching'      // 正在搜索资料
  | 'reading_profile' // 正在了解学习情况
  | 'reading_memory'  // 正在回顾学习记录
  | 'searching_knowledge' // 正在检索知识库
  | 'generating'     // 正在生成回答
  | 'generating_diagram' // 正在生成图解

/** 工具名称到状态的映射 */
export const TOOL_NAME_TO_STAGE: Record<string, AgentStage> = {
  'duckduckgo_search': 'searching',
  'duckduckgo_instant_answer': 'searching',
  'tavily_search': 'searching',
  'spark_search': 'searching',
  'open_web_page': 'searching',
  'find_in_web_page': 'searching',
  'extract_web_links': 'searching',
  'read_web_pdf': 'searching',
  'get_learner_profile': 'reading_profile',
  'get_long_term_memory': 'reading_memory',
  'search_knowledge_base': 'searching_knowledge',
}

/** 状态对应的展示文案 */
export const STAGE_MESSAGE: Record<AgentStage, string> = {
  idle: '',
  classifying: '正在分析问题...',
  analyzing_files: '正在分析附件...',
  searching: '正在搜索资料...',
  reading_profile: '正在了解你的学习情况...',
  reading_memory: '正在回顾学习记录...',
  searching_knowledge: '正在检索知识库...',
  generating: '正在生成回答...',
  generating_diagram: '正在生成教学图解...',
}

export interface ChatMsg {
  id: number
  role: 'user' | 'ai'
  content: string
  time: string
  attachments?: Attachment[] | null
  teachingDiagram?: TeachingDiagram | null
  teachingDiagramGenerating?: boolean
  /** @deprecated 使用 agentStage 替代 */
  searchStage?: string
  /** @deprecated 使用 agentStage 替代 */
  searchMessage?: string
  /** Agent 当前工作状态 - 基于后端事件 */
  agentStage?: AgentStage
  /** 当前正在执行的工具列表 */
  activeTools?: string[]
  agentActivities?: AgentActivity[]
  contextCompressionStage?: ContextCompressionStage
  contextCompressionMessage?: string
}

export const normalizeTeachingDiagram = (diagram: TeachingDiagram | null | undefined): TeachingDiagram | null => {
  if (!diagram || typeof diagram !== 'object') return null
  if (!['comparison', 'flowchart', 'sequence', 'framework', 'summary', 'hierarchy'].includes(diagram.graph_type)) return null
  if (!diagram.title || !diagram.visual_content || !diagram.teaching_content) return null
  return diagram
}

export const getDocumentType = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (['doc', 'docx'].includes(ext)) return 'word'
  if (['xls', 'xlsx'].includes(ext)) return 'excel'
  if (['pdf'].includes(ext)) return 'pdf'
  return 'other'
}

export const getDocumentIconColor = (type: string) => {
  if (type === 'word') return '#2563EB'
  if (type === 'excel') return '#16A34A'
  if (type === 'pdf') return '#DC2626'
  return '#64748B'
}

export const formatRelativeTime = (dateStr: string) => {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return new Date(dateStr).toLocaleDateString()
}

const isCjkCharacter = (char: string): boolean => {
  return /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/.test(char)
}

export const isInsideOpenFence = (text: string): boolean => {
  const fences = text.match(/(^|\n)(`{3,}|~{3,})/g)
  return !!fences && fences.length % 2 === 1
}

const takeAsciiWordUnit = (text: string): number => {
  const word = text.match(/^[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*/)
  if (!word) return 1
  let take = word[0].length
  while (take < text.length && /\s/.test(text[take] || '')) {
    take += 1
  }
  return take
}

export const takeNextStreamUnit = (text: string, inCodeBlock: boolean): number => {
  if (!text) return 0
  if (text.startsWith('\r\n')) return 2
  if (text.startsWith('\n')) return 1
  const listMarker = text.match(/^(?:[-*+]\s|\d+\.\s)/)
  if (listMarker) return listMarker[0].length
  const fenceMarker = text.match(/^(?:`{3,}|~{3,})/)
  if (fenceMarker) return fenceMarker[0].length
  const currentChar = text[0] || ''
  if (inCodeBlock) {
    if (/^[ \t]+/.test(text)) {
      return (text.match(/^[ \t]+/)?.[0].length) || 1
    }
    if (/[A-Za-z0-9_]/.test(currentChar)) {
      return Math.min(takeAsciiWordUnit(text), 3)
    }
    return 1
  }
  if (isCjkCharacter(currentChar)) return 1
  if (/[A-Za-z0-9_]/.test(currentChar)) {
    return takeAsciiWordUnit(text)
  }
  if (/\s/.test(currentChar)) {
    return 1
  }
  return 1
}
