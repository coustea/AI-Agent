// 资源制品解析模块：从后端返回的灵活数据结构中提取内容、题目、阅读推荐

export type ResourceArtifactLike = Record<string, any> | string | null | undefined // 资源制品的灵活类型（对象、字符串或空）

function asText(value: unknown): string { // 将任意值转为文本字符串
  if (typeof value === 'string') return value
  if (value == null) return ''
  return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
}

export function getMarkdownContent(resultData: ResourceArtifactLike): string { // 从资源制品中提取 Markdown 内容
  if (!resultData) return ''
  if (typeof resultData === 'string') return resultData // 字符串直接返回
  const readingData = normalizeReadingArtifact(resultData) // 优先尝试解析为阅读推荐格式
  if (readingData?.resources?.length) {
    return renderReadingRecommendations(readingData.resources)
  }
  return asText( // 按优先级依次尝试提取各字段
    resultData.content ||
    resultData.markdown_content ||
    resultData.full_code ||
    resultData.outline ||
    resultData.agent_output ||
    '',
  )
}

export function parseJsonObject(value: unknown): Record<string, any> | null { // 安全解析 JSON 对象，非对象返回 null
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

function unwrapResourceArtifact(resultData: ResourceArtifactLike): unknown { // 解包嵌套的 resource 字段
  if (!resultData || typeof resultData !== 'object' || Array.isArray(resultData)) return resultData
  return resultData.resource && typeof resultData.resource === 'object'
    ? resultData.resource
    : resultData
}

function ensureOptions(questions: any[]): Record<string, any>[] { // 为判断题补充默认选项（正确/错误）
  if (!Array.isArray(questions)) return []
  return questions.map(q => {
    const type = (q.type || q.question_type)?.toLowerCase() || ''
    if (['true_false', 'truefalse', 'tf'].includes(type) && (!Array.isArray(q.options) || q.options.length === 0)) {
      return {
        ...q,
        options: [
          { label: 'A', content: '正确' },
          { label: 'B', content: '错误' }
        ]
      }
    }
    return q
  })
}

function quizQuestionsFromRecord(record: Record<string, any>): Record<string, any>[] { // 从多种嵌套结构中提取题目列表
  if (Array.isArray(record.questions)) return ensureOptions(record.questions) // 顶层 questions 字段

  const content = record.content
  if (content && typeof content === 'object' && !Array.isArray(content)) { // content.questions
    if (Array.isArray(content.questions)) return ensureOptions(content.questions)
  }

  const parsedContent = parseJsonObject(content) // content 为 JSON 字符串时解析
  if (parsedContent && Array.isArray(parsedContent.questions)) return ensureOptions(parsedContent.questions)

  const parsedRawJson = parseJsonObject(record.raw_json) // raw_json 字段
  if (parsedRawJson && Array.isArray(parsedRawJson.questions)) return ensureOptions(parsedRawJson.questions)

  const data = record.data // data.questions 字段
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    if (Array.isArray(data.questions)) return ensureOptions(data.questions)
  }

  return []
}

export function normalizeQuizQuestions(resultData: ResourceArtifactLike): Record<string, any>[] { // 规范化题目数据，统一提取为题目列表
  const unwrapped = unwrapResourceArtifact(resultData)
  const parsedRoot = parseJsonObject(unwrapped)

  if (parsedRoot) return quizQuestionsFromRecord(parsedRoot)
  if (unwrapped && typeof unwrapped === 'object' && !Array.isArray(unwrapped)) {
    return quizQuestionsFromRecord(unwrapped as Record<string, any>)
  }

  return []
}

function normalizeReadingCollection(data: Record<string, any>): Record<string, any> | null { // 从对象中查找阅读推荐集合并展平嵌套
  const collectionKeys = ['resources', 'recommendations', 'items'] // 可能的集合字段名
  for (const key of collectionKeys) {
    if (Array.isArray(data[key])) {
      const resources = flattenReadingResources(data[key])
      return key === 'resources' ? { ...data, resources } : { ...data, resources }
    }
  }
  return null
}

function flattenReadingResources(items: unknown[]): unknown[] { // 递归展平嵌套的阅读推荐资源列表
  const flattened: unknown[] = []
  for (const item of items) {
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      const record = item as Record<string, any>
      if (Array.isArray(record.resources)) { // 嵌套 resources → 递归展开
        flattened.push(...flattenReadingResources(record.resources))
        continue
      }
      if (Array.isArray(record.recommendations)) { // 嵌套 recommendations → 递归展开
        flattened.push(...flattenReadingResources(record.recommendations))
        continue
      }
      if (Array.isArray(record.items)) { // 嵌套 items → 递归展开
        flattened.push(...flattenReadingResources(record.items))
        continue
      }
    }
    flattened.push(item)
  }
  return flattened
}

export function normalizeReadingArtifact(resultData: ResourceArtifactLike): Record<string, any> | null { // 规范化阅读推荐数据
  if (!resultData) return null
  if (Array.isArray(resultData)) return { resources: resultData } // 数组直接包装
  if (typeof resultData !== 'object') return null

  let data = resultData as Record<string, any>
  if (data.resource && typeof data.resource === 'object' && !Array.isArray(data.resource)) { // 解包 resource 嵌套
    data = data.resource as Record<string, any>
  }

  const direct = normalizeReadingCollection(data) // 直接从对象提取
  if (direct) return direct

  if (typeof data.content === 'object' && data.content !== null && !Array.isArray(data.content)) { // 从 content 对象提取
    const fromContent = normalizeReadingCollection(data.content as Record<string, any>)
    if (fromContent) return fromContent
  }

  const parsedContent = parseJsonObject(data.content) // 从 content JSON 字符串提取
  if (parsedContent) {
    const fromParsed = normalizeReadingCollection(parsedContent)
    if (fromParsed) return fromParsed
  }

  return null
}

function renderReadingRecommendations(recommendations: unknown[]): string { // 将阅读推荐列表渲染为 Markdown 文本
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
