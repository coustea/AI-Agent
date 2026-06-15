export type ThemeType = 'theme-logic-blue' | 'theme-mac-light' | 'theme-notion-light'

export type LayoutType = 'FocusTitle' | 'SplitScreen' | 'BentoGrid' | 'LayerStack'

export interface SlideMetadata {
  speaker_notes?: string
  transition?: 'fade' | 'slide' | 'zoom' | 'none'
  background_override?: string
}

// ---------------------------------------------------------
// Blocks
// ---------------------------------------------------------
export type BlockType =
  | 'Heading'
  | 'Text'
  | 'Callout'
  | 'Code'
  | 'BigNumber'
  | 'Formula'
  | 'Timeline'
  | 'Terminal'

export interface BaseBlock {
  id: string
  type: BlockType
}

export interface BlockHeading extends BaseBlock {
  type: 'Heading'
  level: 1 | 2 | 3
  content: string
}

export interface BlockText extends BaseBlock {
  type: 'Text'
  content: string
  format?: 'markdown' | 'plain'
}

export interface BlockCallout extends BaseBlock {
  type: 'Callout'
  intent: 'info' | 'warning' | 'success' | 'danger'
  icon: string
  content: string
}

export interface BlockCode extends BaseBlock {
  type: 'Code'
  language: string
  code: string
  highlightLines?: number[]
}

export interface BlockBigNumber extends BaseBlock {
  type: 'BigNumber'
  number: string
  unit?: string
  label: string
}

export interface BlockFormula extends BaseBlock {
  type: 'Formula'
  formula: string
}

export interface TimelineStep {
  time: string
  title: string
  description?: string
}

export interface BlockTimeline extends BaseBlock {
  type: 'Timeline'
  steps: TimelineStep[]
}

export interface BlockTerminal extends BaseBlock {
  type: 'Terminal'
  command?: string
  output: string
}

export type SlideBlock =
  | BlockHeading
  | BlockText
  | BlockCallout
  | BlockCode
  | BlockBigNumber
  | BlockFormula
  | BlockTimeline
  | BlockTerminal

// ---------------------------------------------------------
// Layouts
// ---------------------------------------------------------
export interface LayoutConfig {
  ratio?: string // For SplitScreen e.g., '4:6'
  [key: string]: any
}

export interface SlideData {
  id: string
  layout: LayoutType
  layoutConfig?: LayoutConfig
  slots: Record<string, SlideBlock[]>
  metadata?: SlideMetadata
}

// ---------------------------------------------------------
// Document
// ---------------------------------------------------------
export interface PPTDocument {
  template_id: ThemeType
  topic: string
  author?: string
  date?: string
  slides: SlideData[]
}
