import type {
  GeneratedResourceBundle,
  GeneratedResourceItem,
} from '@/features/resource/model/resource'
import { getArtifactLabel } from '@/shared/content/kind'
import type { ResourceArtifactLike } from '@/shared/content/artifact'

export type ResourceCard = {
  id: string
  type: string
  title: string
  summary: string
  format: string
  content: ResourceArtifactLike
  resource: GeneratedResourceItem
}

export const RESOURCE_ORDER = [
  'content',
  'mindmap',
  'quiz',
  'code',
  'reading',
  'ppt',
  'cartoon',
] as const

const RESOURCE_TYPES = new Set<string>(RESOURCE_ORDER)

export function getResourceBundleSubtitle(bundle: GeneratedResourceBundle | null) {
  const title = String(bundle?.title || '').trim()

  if (title && title !== '个性化学习资源包') {
    return title
  }

  return '本次生成的课程讲解、练习与拓展内容已整理完成'
}

export function getResourceCards(bundle: GeneratedResourceBundle | null): ResourceCard[] {
  const resources = bundle?.resources
  const subtitle = getResourceBundleSubtitle(bundle)

  if (!Array.isArray(resources)) return []

  return resources
    .map(resource => normalizeCard(resource, subtitle))
    .filter((card): card is ResourceCard => card !== null)
    .sort((first, second) => getResourceOrder(first.type) - getResourceOrder(second.type))
}

export function getResourceActionText(type: string) {
  const actionMap: Record<string, string> = {
    content: '查看课程讲解',
    mindmap: '打开思维导图',
    quiz: '查看练习题',
    code: '查看代码实操',
    reading: '查看拓展阅读',
    ppt: '查看教学课件',
    cartoon: '查看动画讲解',
  }

  return actionMap[type] || '查看资源内容'
}

export function formatResourceTime(time: string | null) {
  if (!time) return ''

  const date = new Date(time)
  if (Number.isNaN(date.getTime())) return ''

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function normalizeCard(resource: GeneratedResourceItem, bundleSubtitle: string): ResourceCard | null {
  const type = resource.type

  if (!RESOURCE_TYPES.has(type)) {
    return null
  }

  if (!hasContent(resource.content, type)) return null

  return {
    id: String(resource.id ?? type),
    type,
    title: getTitle(resource, type, bundleSubtitle),
    summary: getSummary(resource, type),
    format: getFormat(resource, type),
    content: resource.content,
    resource,
  }
}

function getResourceOrder(type: string) {
  const index = RESOURCE_ORDER.indexOf(type as (typeof RESOURCE_ORDER)[number])
  return index === -1 ? 99 : index
}

function getTitle(resource: GeneratedResourceItem, type: string, bundleSubtitle: string) {
  const title = typeof resource.title === 'string' ? resource.title.trim() : ''
  return title || `${getArtifactLabel(type)} · ${bundleSubtitle}`
}

function getSummary(resource: GeneratedResourceItem, type: string) {
  const summary = [
    resource.metadata?.summary,
  ].find(value => typeof value === 'string' && value.trim())

  if (typeof summary === 'string') return summary.trim()

  const defaults: Record<string, string> = {
    content: '围绕学习目标组织系统讲解，帮助建立完整、清晰的知识框架。',
    mindmap: '梳理核心概念、层级关系和知识依赖，形成直观的知识结构。',
    quiz: '通过不同题型检测理解程度，用于学习后的即时练习与巩固。',
    code: '提供可阅读、可运行的代码案例，帮助将理论知识转化为实践能力。',
    reading: '补充相关课程资料与拓展阅读，便于继续深入学习。',
    ppt: '整合重点内容形成结构化课件，适合课堂展示与快速复习。',
    cartoon: '通过动画呈现概念变化、执行过程与知识之间的关系。',
  }

  return defaults[type] || '根据本次学习需求生成的个性化学习资源。'
}

function getFormat(resource: GeneratedResourceItem, type: string) {
  const raw = resource.format

  if (typeof raw === 'string' && raw.trim()) {
    const formatMap: Record<string, string> = {
      markdown: 'Markdown',
      md: 'Markdown',
      markmap: 'Markmap',
      json: 'JSON',
      code: 'Code',
      links: 'Links',
      pdf: 'PDF',
      ppt: 'Slides',
      pptx: 'Slides',
      slides: 'Slides',
      mp4: 'Video',
      video: 'Video',
    }
    return formatMap[raw.trim().toLowerCase()] || raw.trim()
  }

  const formats: Record<string, string> = {
    content: 'Markdown',
    mindmap: 'Markmap',
    quiz: 'JSON',
    code: 'Code',
    reading: 'Links',
    ppt: 'Slides',
    cartoon: 'Video',
  }

  return formats[type] || 'Resource'
}

function hasContent(value: unknown, type: string) {
  if (type === 'ppt' || type === 'cartoon') return true
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  return Boolean(value && typeof value === 'object' && Object.keys(value).length > 0)
}
