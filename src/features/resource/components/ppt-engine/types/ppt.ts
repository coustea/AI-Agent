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
  id: string
  index: number
  role: SlideRole
  title: string
  subtitle?: string | null
  layout: LayoutId
  slots: Record<string, SlideBlock[]>
  takeaway: string
  speaker_notes: string
}

export interface PPTDocument {
  template_id: 'teaching-lesson'
  theme_id: ThemeType
  title: string
  audience: string
  slides: PptSlide[]
}

export type PptParseResult =
  | { ok: true; document: PPTDocument }
  | { ok: false; reason: string; details?: string[] }

const layoutSlots = (manifest.layouts ?? {}) as Record<string, { slots?: string[] }>
const knownThemes = new Set<string>(Array.isArray(manifest.themes) ? manifest.themes : [])
const knownLayouts = new Set<string>(Object.keys(layoutSlots))
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
      return isNonEmptyString(block.content) && block.content.length <= 120 && (block.format === 'plain' || block.format === 'markdown')
    case 'Callout':
      return isNonEmptyString(block.content) && block.content.length <= 100
        && isNonEmptyString(block.icon) && block.icon.length <= 4
        && ['info', 'warning', 'success', 'danger'].includes(String(block.intent))
    case 'KeyPoint':
      return isNonEmptyString(block.label) && block.label.length <= 16
        && isNonEmptyString(block.content) && block.content.length <= 48
    case 'Diagram':
      if (!['LR', 'TB', 'RL', 'BT'].includes(String(block.direction)) || !Array.isArray(block.nodes) || !Array.isArray(block.edges)) return false
      if (block.nodes.length < 2 || block.nodes.length > 8 || block.edges.length < 1 || block.edges.length > 12) return false
      return block.nodes.every(node => isRecord(node)
        && isNonEmptyString(node.id) && node.id.length <= 24
        && isNonEmptyString(node.label) && node.label.length <= 36)
    case 'FlowChart':
      return Array.isArray(block.steps)
        && block.steps.length >= 3
        && block.steps.length <= 6
        && block.steps.every(step => isRecord(step)
          && isNonEmptyString(step.step_id)
          && isNonEmptyString(step.title)
          && isNonEmptyString(step.description))
    case 'Table': {
      if (!isStringArray(block.columns, 2) || block.columns.length > 4 || !Array.isArray(block.rows) || block.rows.length < 2 || block.rows.length > 6) return false
      const columnCount = block.columns.length
      return block.rows.every(row => isStringArray(row) && row.length === columnCount)
    }
    case 'CardList':
      return Array.isArray(block.cards)
        && block.cards.length >= 2
        && block.cards.length <= 5
        && block.cards.every(card => isRecord(card)
          && isNonEmptyString(card.title)
          && card.title.length <= 24
          && isNonEmptyString(card.content)
          && card.content.length <= 72)
    case 'Formula':
      return isNonEmptyString(block.formula) && block.formula.length <= 120
    case 'CodeSnippet':
      if (!isNonEmptyString(block.language) || !isNonEmptyString(block.code)) return false
      const codeLineCount = block.code.split('\n').filter(line => line.trim()).length
      return block.language.length <= 24
        && codeLineCount >= 1
        && codeLineCount <= 20
    default:
      return false
  }
}

function validateSlide(slide: unknown, errors: string[], index: number): slide is PptSlide {
  if (!isRecord(slide)) {
    errors.push(`slides[${index}] 不是对象`)
    return false
  }
  if (!isNonEmptyString(slide.id)) errors.push(`slides[${index}].id 缺失`)
  if (!Number.isInteger(slide.index)) errors.push(`slides[${index}].index 缺失或非法`)
  if (typeof slide.role !== 'string' || !validRoles.has(slide.role)) errors.push(`slides[${index}].role 非法`)
  if (!isNonEmptyString(slide.title)) errors.push(`slides[${index}].title 缺失`)
  if (typeof slide.layout !== 'string' || !knownLayouts.has(slide.layout)) errors.push(`slides[${index}].layout 非法`)
  if (slide.subtitle !== undefined && slide.subtitle !== null && typeof slide.subtitle !== 'string') errors.push(`slides[${index}].subtitle 非法`)
  if (!isNonEmptyString(slide.takeaway) || slide.takeaway.length > 60) errors.push(`slides[${index}].takeaway 非法`)
  if (!isNonEmptyString(slide.speaker_notes) || slide.speaker_notes.length < 10 || slide.speaker_notes.length > 140) errors.push(`slides[${index}].speaker_notes 非法`)
  if (!isRecord(slide.slots)) {
    errors.push(`slides[${index}].slots 缺失`)
    return false
  }
  const slots = slide.slots as Record<string, unknown>
  const expectedSlots = layoutSlots[String(slide.layout)]?.slots ?? []
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
  if (payload.template_id !== 'teaching-lesson') {
    errors.push('template_id 必须为 teaching-lesson')
  }
  if (typeof payload.theme_id !== 'string' || !knownThemes.has(payload.theme_id)) {
    errors.push('theme_id 非法或缺失')
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
      if (typeof slide.id === 'string') {
        if (slideIds.has(slide.id)) errors.push(`slides[${index}].id 重复`)
        slideIds.add(slide.id)
      }
    })
    if (isRecord(payload.slides[0]) && payload.slides[0].role !== 'cover') errors.push('首张幻灯片必须是 cover')
    const lastSlide = payload.slides[payload.slides.length - 1]
    if (isRecord(lastSlide) && lastSlide.role !== 'summary') errors.push('末张幻灯片必须是 summary')
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