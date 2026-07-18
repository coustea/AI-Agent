import type { ChatVideoArtifact, StructuredTeachingDiagram, TeachingDiagram } from '@/features/chat/types/chat'

export interface PendingFile {
  file?: File
  url?: string
  localUrl?: string
  fileType: 'image' | 'document' | string
  name: string
  size?: number
  mimeType?: string
}

export interface Attachment {
  url: string
  type: 'image' | 'document' | string
  name: string
  size?: number
  mimeType?: string
}

// 知识库来源条目
export interface KnowledgeSource {
  source: string       // 来源类型（如 "knowledge_base"）
  title: string        // 书名/章节标题
  heading?: string     // 章节/位置
  summary: string      // 内容摘要
  url?: string         // URL（如果有）
  score?: number       // 相关性分数
}

export interface AgentActivityDetail {
  agent?: string
  action?: string
  tool_name?: string
  input?: string
  output?: string
  error?: string
  duration_ms?: number | null
  analysis_type?: string
  files?: string[]
}

export interface AgentActivity {
  activity_id: string
  kind: 'agent' | 'tool' | 'attachment' | 'workflow'
  stage?: string
  status: 'running' | 'done' | 'failed'
  tool_name?: string
  title: string
  summary?: string
  message?: string
  detail?: AgentActivityDetail
}

export interface ChatMsg {
  id: number
  userMessageId?: number
  role: 'user' | 'ai'
  content: string
  time: string
  attachments?: Attachment[] | null
  teachingDiagram?: TeachingDiagram | null
  teachingDiagramGenerating?: boolean
  video?: ChatVideoArtifact | null
  videoPreparing?: boolean
  videoOnly?: boolean
  agentActivities?: AgentActivity[]
  sources?: KnowledgeSource[]  // 知识库来源
}

// 将活动中所有 running 状态统一标记为 done/failed
export const assignPersistedAssistantMessageId = (message: ChatMsg, savedMessageId: unknown): number => {
  if (typeof savedMessageId === 'number' && Number.isSafeInteger(savedMessageId) && savedMessageId > 0) {
    message.id = savedMessageId
  }
  return message.id
}

export const finalizeRunningAgentActivities = (
  activities: AgentActivity[] | undefined,
  status: Extract<AgentActivity['status'], 'done' | 'failed'>,
): AgentActivity[] => (
  (activities || []).map(activity => (
    activity.status === 'running'
      ? { ...activity, status }
      : activity
  ))
)

export const finalizeAssistantGeneration = (
  message: ChatMsg,
  status: Extract<AgentActivity['status'], 'done' | 'failed'>,
): void => {
  message.agentActivities = status === 'done'
    ? []
    : finalizeRunningAgentActivities(message.agentActivities, status)
  message.teachingDiagramGenerating = false
}

const SUPPORTED_DIAGRAM_TYPES = new Set([
  'comparison',
  'flowchart',
  'sequence',
  'framework',
  'summary',
  'hierarchy',
  'tree',
  'grid',
  'protocol',
  'timeline',
])

const isStructuredTeachingDiagram = (diagram: unknown): diagram is StructuredTeachingDiagram => {
  if (!diagram || typeof diagram !== 'object') return false
  const candidate = diagram as Partial<StructuredTeachingDiagram>
  return Boolean(
    typeof candidate.graph_type === 'string'
    && SUPPORTED_DIAGRAM_TYPES.has(candidate.graph_type)
    && candidate.title
    && candidate.visual_content
    && candidate.teaching_content,
  )
}

// 兼容旧的结构化 payload、PNG payload，以及 PNG 生成失败时保留的结构化回退。
export const normalizeTeachingDiagram = (diagram: unknown): TeachingDiagram | null => {
  if (!diagram || typeof diagram !== 'object') return null
  const candidate = diagram as Record<string, unknown>
  if (candidate.kind === 'image') {
    return typeof candidate.title === 'string' && typeof candidate.image_url === 'string' && candidate.image_url
      ? candidate as unknown as TeachingDiagram
      : null
  }
  if (candidate.kind === 'fallback') {
    return isStructuredTeachingDiagram(candidate.diagram)
      && typeof candidate.render_error === 'string'
      && typeof candidate.retryable === 'boolean'
      ? candidate as unknown as TeachingDiagram
      : null
  }
  return isStructuredTeachingDiagram(candidate) ? candidate : null
}

// 根据文件名获取文档类型分类
export interface InputToolState {
  uploadingFile: boolean
  enableWebSearch: boolean
  needTeachingDiagram: boolean
  needVideo?: boolean
}

export const getInputToolStateKey = ({
  uploadingFile,
  enableWebSearch,
  needTeachingDiagram,
  needVideo = false,
}: InputToolState): string => (
  [
    uploadingFile ? 'uploading' : 'idle',
    enableWebSearch ? 'web-on' : 'web-off',
    needTeachingDiagram ? 'diagram-on' : 'diagram-off',
    needVideo ? 'video-on' : 'video-off',
  ].join(':')
)

export const getDocumentType = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (['doc', 'docx'].includes(ext)) return 'word'
  if (['xls', 'xlsx'].includes(ext)) return 'excel'
  if (['ppt', 'pptx'].includes(ext)) return 'ppt'
  if (['pdf'].includes(ext)) return 'pdf'
  if (['md', 'txt', 'log'].includes(ext)) return 'text'
  return 'other'
}

export const getDocumentIconColor = (type: string) => {
  if (type === 'word') return '#2563EB'
  if (type === 'excel') return '#15803D'
  if (type === 'ppt') return '#C2410C'
  if (type === 'pdf') return '#DC2626'
  if (type === 'text') return '#475569'
  return '#64748B'
}

export const formatFileSize = (size?: number) => {
  if (!size || size <= 0) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(size < 10 * 1024 ? 1 : 0)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

// 格式化相对时间显示（如"3分钟前"）
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

export const isCjkCharacter = (char: string): boolean => {
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
  while (take < text.length && /\s/.test(text[take] || '')) take += 1
  return take
}

// 流式渲染：取下一个渲染单元的长度（支持 CJK、英文单词、代码块）
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
    if (/^[ \t]+/.test(text)) return text.match(/^[ \t]+/)?.[0].length || 1
    if (/[A-Za-z0-9_]/.test(currentChar)) return Math.min(takeAsciiWordUnit(text), 3)
    return 1
  }
  if (isCjkCharacter(currentChar)) return 1
  if (/[A-Za-z0-9_]/.test(currentChar)) return takeAsciiWordUnit(text)
  return 1
}
