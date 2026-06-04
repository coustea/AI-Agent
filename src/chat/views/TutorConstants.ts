import type { TeachingDiagram, KnowledgeSource } from '@/chat/types/chat'

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

export interface ChatMsg {
  id: number
  role: 'user' | 'ai'
  content: string
  time: string
  attachments?: Attachment[] | null
  teachingDiagram?: TeachingDiagram | null
  teachingDiagramGenerating?: boolean
  searchStage?: string
  searchMessage?: string
  knowledgeSources?: KnowledgeSource[]
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
