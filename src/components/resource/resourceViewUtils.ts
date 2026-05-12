import { marked } from 'marked'

export type ResourceArtifactLike = Record<string, any> | string | null | undefined

export function getFileUrl(resultData: ResourceArtifactLike): string {
  if (!resultData || typeof resultData !== 'object') return ''
  return resultData.file_url || resultData.file_path || resultData.fileUrl || resultData.path || resultData.url || ''
}

export function getFileCategory(fileUrl: string): string {
  if (!fileUrl) return ''
  const cleanUrl = fileUrl.split('?')[0] || ''
  const ext = cleanUrl.split('.').pop()?.toLowerCase() || ''
  if (['html', 'htm'].includes(ext)) return 'html'
  if (['md', 'markdown'].includes(ext)) return 'markdown'
  if (['pdf'].includes(ext)) return 'pdf'
  if (['json'].includes(ext)) return 'json'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return 'image'
  if (['mp4', 'webm', 'ogg', 'mov'].includes(ext)) return 'video'
  if (['pptx', 'ppt'].includes(ext)) return 'pptx'
  return ext || 'other'
}

export function getFileName(fileUrl: string): string {
  if (!fileUrl) return '未命名文件'
  const cleanUrl = fileUrl.split('?')[0] || ''
  return cleanUrl.split('/').pop() || '未命名文件'
}

export function asText(value: unknown): string {
  if (typeof value === 'string') return value
  if (value == null) return ''
  return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
}

export function getMarkdownContent(resultData: ResourceArtifactLike): string {
  if (!resultData) return ''
  if (typeof resultData === 'string') return resultData
  const readingData = normalizeReadingArtifact(resultData)
  if (readingData?.resources?.length) {
    return renderReadingRecommendations(readingData.resources)
  }
  return asText(
    resultData.content ||
    resultData.markdown_content ||
    resultData.full_code ||
    resultData.outline ||
    resultData.agent_output ||
    '',
  )
}

export function renderMarkdown(text: string): string {
  return text ? String(marked.parse(text)) : ''
}

export function parseJsonObject(value: unknown): Record<string, any> | null {
  if (!value) return null
  if (typeof value === 'object' && !Array.isArray(value)) return value as Record<string, any>
  if (typeof value !== 'string') return null
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed as Record<string, any>
      : null
  } catch {
    return null
  }
}

function normalizeReadingCollection(data: Record<string, any>): Record<string, any> | null {
  const collectionKeys = ['resources', 'recommendations', 'items']
  for (const key of collectionKeys) {
    if (Array.isArray(data[key])) {
      return key === 'resources' ? data : { ...data, resources: data[key] }
    }
  }
  return null
}

export function normalizeReadingArtifact(resultData: ResourceArtifactLike): Record<string, any> | null {
  if (!resultData) return null
  if (Array.isArray(resultData)) return { resources: resultData }
  if (typeof resultData !== 'object') return null

  let data = resultData as Record<string, any>
  if (data.resource && typeof data.resource === 'object' && !Array.isArray(data.resource)) {
    data = data.resource as Record<string, any>
  }

  const direct = normalizeReadingCollection(data)
  if (direct) return direct

  if (typeof data.content === 'object' && data.content !== null && !Array.isArray(data.content)) {
    const fromContent = normalizeReadingCollection(data.content as Record<string, any>)
    if (fromContent) return fromContent
  }

  const parsedContent = parseJsonObject(data.content)
  if (parsedContent) {
    const fromParsed = normalizeReadingCollection(parsedContent)
    if (fromParsed) return fromParsed
  }

  return null
}

/**
 * 通用的资源内容提取函数，支持多种数据结构格式
 * 用于从后端返回的嵌套数据结构中提取实际内容
 */
export function extractResourceContent(
  resultData: ResourceArtifactLike,
  contentKeys: string[] = ['content', 'markdown_content', 'source', 'mermaid', 'outline']
): string {
  if (!resultData) return ''
  if (typeof resultData === 'string') return resultData
  
  let data = resultData as Record<string, any>
  
  // 处理 resource 包装层
  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }
  
  // 从 content 字段提取
  const content = data.content
  
  // content 是字符串
  if (typeof content === 'string' && content.trim()) {
    const parsed = parseJsonObject(content)
    if (parsed) {
      for (const key of contentKeys) {
        if (parsed[key] && typeof parsed[key] === 'string') {
          return parsed[key]
        }
      }
    }
    return content
  }
  
  // content 是对象
  if (typeof content === 'object' && content !== null) {
    for (const key of contentKeys) {
      if (content[key] && typeof content[key] === 'string') {
        return content[key]
      }
    }
  }
  
  // 回退到 data 第一层
  for (const key of contentKeys) {
    if (data[key] && typeof data[key] === 'string') {
      return data[key]
    }
  }
  
  return ''
}

export function renderReadingRecommendations(recommendations: unknown[]): string {
  const lines = ['# 拓展阅读', '']
  recommendations.forEach((item, index) => {
    const record = item && typeof item === 'object' ? item as Record<string, any> : {}
    const authors = Array.isArray(record.authors) ? record.authors.join(', ') : record.author_or_source || record.source || ''
    lines.push(
      `### ${index + 1}. ${asText(record.title || '未命名资源')}`,
      `- 来源：${asText(authors || '未知')}`,
      `- 类型：${asText(record.type || 'resource')}`,
      `- 推荐理由：${asText(record.recommend_reason || record.relevance || '与当前主题相关')}`,
      `- 摘要：${asText(record.description || record.abstract || record.summary || '')}`,
      '',
    )
  })
  return lines.join('\n').trim()
}
