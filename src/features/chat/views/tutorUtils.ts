import type { RunState } from '@/features/chat/types/chatRun'

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

export interface ChatMsg {
  id: number
  role: 'user' | 'ai'
  content: string
  time: string
  attachments?: Attachment[] | null
  run?: RunState
  localError?: string
}

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

