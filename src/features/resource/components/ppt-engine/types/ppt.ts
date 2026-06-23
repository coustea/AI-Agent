import manifest from '@ppt-manifest'

export type ThemeType = 'logic-blue' | 'paper-light' | 'lab-light'
export type LayoutId = 'HeroCover' | 'DualPane' | 'TriplePane' | 'DiagramFocus' | 'FlowCanvas' | 'CompareTable' | 'CardCluster' | 'KnowledgeMap'

export type SlideRole =
  | 'cover'
  | 'objectives'
  | 'prerequisite'
  | 'problem_intro'
  | 'roadmap'
  | 'concept'
  | 'analogy'
  | 'principle_diagram'
  | 'process_demo'
  | 'mechanism_breakdown'
  | 'concept_relation'
  | 'concept_compare'
  | 'misconception'
  | 'summary'
  | 'next_steps'
  | 'algorithm_visualization'
  | 'code_walkthrough'
  | 'architecture_diagram'

export type Difficulty = 'beginner' | 'intermediate' | 'advanced'

export type BlockType =
  | 'Text'
  | 'Callout'
  | 'KeyPoint'
  | 'Diagram'
  | 'FlowChart'
  | 'Table'
  | 'CardList'
  | 'Formula'
  | 'CodeSnippet'

export interface BaseBlock {
  block_id: string
  type: string
}

export interface TextBlock extends BaseBlock {
  type: 'Text'
  content: string
  format: 'plain' | 'markdown'
}

export interface CalloutBlock extends BaseBlock {
  type: 'Callout'
  intent: 'info' | 'warning' | 'success' | 'danger'
  icon: string
  content: string
}

export interface KeyPointBlock extends BaseBlock {
  type: 'KeyPoint'
  label: string
  content: string
}

export interface DiagramNode {
  id: string
  label: string
}

export interface DiagramEdge {
  source: string
  target: string
  label?: string | null
}

export interface DiagramBlock extends BaseBlock {
  type: 'Diagram'
  direction: 'LR' | 'TB' | 'RL' | 'BT'
  nodes: DiagramNode[]
  edges: DiagramEdge[]
}

export interface FlowStep {
  step_id: string
  title: string
  description: string
  state_before?: string | null
  state_after?: string | null
}

export interface FlowChartBlock extends BaseBlock {
  type: 'FlowChart'
  steps: FlowStep[]
}

export interface TableBlock extends BaseBlock {
  type: 'Table'
  columns: string[]
  rows: string[][]
}

export interface CardItem {
  title: string
  content: string
  icon?: string | null
}

export interface CardListBlock extends BaseBlock {
  type: 'CardList'
  cards: CardItem[]
}

export interface FormulaBlock extends BaseBlock {
  type: 'Formula'
  formula: string
}

export interface CodeHighlight {
  line: number
  note: string
}

export interface CodeSnippetBlock extends BaseBlock {
  type: 'CodeSnippet'
  language: string
  code: string
  highlights: CodeHighlight[]
}

export type SlideBlock =
  | TextBlock
  | CalloutBlock
  | KeyPointBlock
  | DiagramBlock
  | FlowChartBlock
  | TableBlock
  | CardListBlock
  | FormulaBlock
  | CodeSnippetBlock

export interface PptSlide {
  id?: string // 可选，前端自动生成
  index?: number // 可选，前端自动计算
  role: SlideRole
  title: string
  subtitle?: string | null
  layout?: LayoutId // 可选，前端根据 role 推断
  slots: Record<string, SlideBlock[]>
  takeaway: string
  speaker_notes?: string // 可选
}

export interface PPTDocument {
  template_id?: 'teaching-lesson' // 可选，前端默认值
  theme_id?: ThemeType // 可选，前端默认 logic-blue
  title: string
  audience: string
  slides: PptSlide[]
}

export type PptParseResult =
  | { ok: true; document: PPTDocument }
  | { ok: false; reason: string; details?: string[] }

const layoutSlots = (manifest.layouts ?? {}) as Record<string, { slots?: string[] }>
const knownThemes = new Set<string>(Array.isArray(manifest.themes) ? manifest.themes : [])
const knownBlockTypes = new Set<string>(Object.keys((manifest.blocks ?? {}) as Record<string, unknown>))
const validRoles = new Set<string>([
  'cover', 'objectives', 'prerequisite', 'problem_intro', 'roadmap', 'concept',
  'analogy', 'principle_diagram', 'process_demo', 'mechanism_breakdown',
  'concept_relation', 'concept_compare', 'misconception', 'summary', 'next_steps',
  'algorithm_visualization', 'code_walkthrough', 'architecture_diagram',
])

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function isStringArray(value: unknown, min = 0): value is string[] {
  return Array.isArray(value) && value.length >= min && value.every(item => typeof item === 'string' && item.trim().length > 0)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function getDocumentPayload(value: unknown): unknown {
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  }
  return value
}

function validateBlock(block: unknown): block is SlideBlock {
  if (!isRecord(block)) return false
  if (!isNonEmptyString(block.block_id)) return false
  if (typeof block.type !== 'string' || !knownBlockTypes.has(block.type)) return false
  switch (block.type) {
    case 'Text':
      return isNonEmptyString(block.content) && (block.format === 'plain' || block.format === 'markdown')
    case 'Callout':
      return isNonEmptyString(block.content)
        && isNonEmptyString(block.icon)
        && ['info', 'warning', 'success', 'danger'].includes(String(block.intent))
    case 'KeyPoint':
      return isNonEmptyString(block.label) && isNonEmptyString(block.content)
    case 'Diagram':
      if (!['LR', 'TB', 'RL', 'BT'].includes(String(block.direction)) || !Array.isArray(block.nodes) || !Array.isArray(block.edges)) return false
      if (block.nodes.length < 2 || block.edges.length < 1) return false
      return block.nodes.every(node => isRecord(node)
        && isNonEmptyString(node.id)
        && isNonEmptyString(node.label))
    case 'FlowChart':
      return Array.isArray(block.steps)
        && block.steps.length >= 2
        && block.steps.every(step => isRecord(step)
          && isNonEmptyString(step.step_id)
          && isNonEmptyString(step.title)
          && isNonEmptyString(step.description))
    case 'Table': {
      if (!isStringArray(block.columns, 2) || !Array.isArray(block.rows) || block.rows.length < 1) return false
      const columnCount = block.columns.length
      return block.rows.every(row => isStringArray(row) && row.length === columnCount)
    }
    case 'CardList':
      return Array.isArray(block.cards)
        && block.cards.length >= 1
        && block.cards.every(card => isRecord(card)
          && isNonEmptyString(card.title)
          && isNonEmptyString(card.content))
    case 'Formula':
      return isNonEmptyString(block.formula)
    case 'CodeSnippet':
      if (!isNonEmptyString(block.language) || !isNonEmptyString(block.code)) return false
      const codeLineCount = block.code.split('\n').filter(line => line.trim()).length
      return codeLineCount >= 1
    default:
      return false
  }
}

function validateSlide(slide: unknown, errors: string[], index: number): slide is PptSlide {
  if (!isRecord(slide)) {
    errors.push(`slides[${index}] 不是对象`)
    return false
  }
  // id 和 index 可选，前端自动生成
  if (slide.id !== undefined && typeof slide.id !== 'string') errors.push(`slides[${index}].id 类型错误`)
  if (slide.index !== undefined && !Number.isInteger(slide.index)) errors.push(`slides[${index}].index 类型错误`)
  if (typeof slide.role !== 'string' || !validRoles.has(slide.role)) errors.push(`slides[${index}].role 非法`)
  if (!isNonEmptyString(slide.title)) errors.push(`slides[${index}].title 缺失`)
  // layout 可选，前端根据 role 推断
  if (slide.layout !== undefined && typeof slide.layout !== 'string') errors.push(`slides[${index}].layout 类型错误`)
  if (slide.subtitle !== undefined && slide.subtitle !== null && typeof slide.subtitle !== 'string') errors.push(`slides[${index}].subtitle 非法`)
  if (!isNonEmptyString(slide.takeaway)) errors.push(`slides[${index}].takeaway 缺失`)
  // speaker_notes 可选
  if (slide.speaker_notes !== undefined && typeof slide.speaker_notes !== 'string') errors.push(`slides[${index}].speaker_notes 类型错误`)
  if (!isRecord(slide.slots)) {
    errors.push(`slides[${index}].slots 缺失`)
    return false
  }
  const slots = slide.slots as Record<string, unknown>
  // layout 可选时，使用默认槽位校验
  const layoutId = typeof slide.layout === 'string' ? slide.layout : 'DualPane'
  const expectedSlots = layoutSlots[layoutId]?.slots ?? ['main']
  for (const slot of expectedSlots) {
    const blocks = slots[slot]
    if (!Array.isArray(blocks) || blocks.length === 0) {
      errors.push(`slides[${index}].slots.${slot} 不能为空`)
      continue
    }
    blocks.forEach((block, blockIndex) => {
      if (!validateBlock(block)) {
        errors.push(`slides[${index}].slots.${slot}[${blockIndex}] 不符合 PPT block 协议`)
      }
    })
  }
  return errors.length === 0
}

export function parsePptDocument(value: unknown): PptParseResult {
  const payload = getDocumentPayload(value)
  if (!isRecord(payload)) {
    return { ok: false, reason: 'PPT 数据不是合法 JSON 对象' }
  }
  const errors: string[] = []
  // template_id 可选，默认 teaching-lesson
  if (payload.template_id !== undefined && payload.template_id !== 'teaching-lesson') {
    errors.push('template_id 必须为 teaching-lesson')
  }
  // theme_id 可选，默认 logic-blue
  if (payload.theme_id !== undefined && (typeof payload.theme_id !== 'string' || !knownThemes.has(payload.theme_id as string))) {
    errors.push('theme_id 非法')
  }
  if (!isNonEmptyString(payload.title)) errors.push('title 缺失')
  if (!isNonEmptyString(payload.audience)) errors.push('audience 缺失')
  if (!Array.isArray(payload.slides) || payload.slides.length < 6 || payload.slides.length > 16) {
    errors.push('slides 缺失或页数超出 6-16 页范围')
  } else {
    const slideIds = new Set<string>()
    payload.slides.forEach((slide, index) => {
      validateSlide(slide, errors, index)
      if (!isRecord(slide)) return
      // 检查重复 ID（仅当 ID 存在时）
      if (typeof slide.id === 'string') {
        if (slideIds.has(slide.id)) errors.push(`slides[${index}].id 重复`)
        slideIds.add(slide.id)
      }
    })
    // 首尾 role 检查放宽
    if (isRecord(payload.slides[0]) && payload.slides[0].role !== 'cover') errors.push('首张幻灯片最好是 cover')
    const lastSlide = payload.slides[payload.slides.length - 1]
    if (isRecord(lastSlide) && lastSlide.role !== 'summary') errors.push('末张幻灯片最好是 summary')
  }
  if (errors.length > 0) {
    return {
      ok: false,
      reason: 'PPT JSON 不符合教学课件协议。',
      details: errors,
    }
  }
  return { ok: true, document: payload as unknown as PPTDocument }
}

/**
 * 根据 role 自动推断 layout
 */
export function inferLayoutByRole(role: SlideRole): LayoutId {
  const roleLayoutMap: Record<string, LayoutId> = {
    cover: 'HeroCover',
    objectives: 'CardCluster',
    prerequisite: 'DualPane',
    problem_intro: 'DualPane',
    roadmap: 'KnowledgeMap',
    concept: 'DualPane',
    analogy: 'DualPane',
    principle_diagram: 'DiagramFocus',
    process_demo: 'FlowCanvas',
    mechanism_breakdown: 'TriplePane',
    concept_relation: 'DiagramFocus',
    concept_compare: 'CompareTable',
    misconception: 'DualPane',
    summary: 'CardCluster',
    next_steps: 'DualPane',
    algorithm_visualization: 'FlowCanvas',
    code_walkthrough: 'DualPane',
    architecture_diagram: 'DiagramFocus',
  }
  return roleLayoutMap[role] || 'DualPane'
}

/**
 * 自动补全 PPT JSON 的缺失字段（id, index, layout, template_id, theme_id）
 * 后端只需提供核心内容，前端调用此函数补全渲染所需字段
 */
export function normalizePptDocument(input: unknown): PPTDocument {
  const payload = getDocumentPayload(input)
  if (!isRecord(payload)) {
    throw new Error('PPT 数据不是合法 JSON 对象')
  }

  const slides = (Array.isArray(payload.slides) ? payload.slides : []).map((slide, index) => {
    const role = typeof slide.role === 'string' ? slide.role as SlideRole : 'concept'
    return {
      id: slide.id || `slide-${index + 1}`,
      index: index,
      role: role,
      title: slide.title || '',
      subtitle: slide.subtitle ?? null,
      layout: slide.layout || inferLayoutByRole(role),
      slots: slide.slots || {},
      takeaway: slide.takeaway || '',
      speaker_notes: slide.speaker_notes,
    } as PptSlide
  })

  return {
    template_id: payload.template_id || 'teaching-lesson',
    theme_id: payload.theme_id || 'logic-blue',
    title: payload.title || '',
    audience: payload.audience || '',
    slides: slides,
  } as PPTDocument
}