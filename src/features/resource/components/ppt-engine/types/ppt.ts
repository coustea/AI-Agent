export type ThemeType = 'theme-logic-blue' | 'theme-mac-light' | 'theme-notion-light'
export type LayoutType =
  | 'cover'
  | 'agenda'
  | 'layer_stack'
  | 'theory_proof'
  | 'process_flow'
  | 'tech_dashboard'
  | 'mixed_two_column'

export interface SlideMetadata {
  speaker_notes?: string
  transition?: 'fade' | 'slide' | 'zoom' | 'none'
  background_override?: string
}

export interface CoverData {
  main_title: string
  sub_title?: string
  lecturer?: string
  date?: string
}

export interface AgendaData {
  list: string[]
}

export interface LayerItem {
  level_name: string
  description: string
  protocols?: string[]
  components?: string[]
}

export interface LayerStackData {
  title: string
  layers: LayerItem[]
}

export interface TheoryProofStep {
  step_title: string
  detail: string
}

export interface TheoryProofData {
  theorem_name: string
  formula_latex: string
  constraints: string[]
  proof_steps: TheoryProofStep[]
}

export interface ProcessFlowStep {
  time_seq: string
  from: string
  to: string
  action: string
  internal_state: string
}

export interface ProcessFlowData {
  flow_title: string
  swimlanes: string[]
  timeline_steps: ProcessFlowStep[]
}

export interface TechDashboardMetric {
  label: string
  value: string
  unit?: string
}

export interface TechDashboardData {
  title: string
  code_snippet: { language: string; code: string }
  terminal_output: string
  stat_metrics: TechDashboardMetric[]
  summary_points: string[]
}

export interface ArchitectureNode {
  id: string
  label: string
  type: string
}

export interface ComparisonTableData {
  dimensions: string[]
  left_features: string[]
  right_features: string[]
}

export interface MixedTwoColumnData {
  title: string
  architecture_nodes?: ArchitectureNode[]
  comparison_table?: ComparisonTableData
  deep_dive_text: string
  inline_code: string
}

export interface CoverSlide {
  layout: 'cover'
  metadata?: SlideMetadata
  data: CoverData
}

export interface AgendaSlide {
  layout: 'agenda'
  metadata?: SlideMetadata
  data: AgendaData
}

export interface LayerStackSlide {
  layout: 'layer_stack'
  metadata?: SlideMetadata
  data: LayerStackData
}

export interface TheoryProofSlide {
  layout: 'theory_proof'
  metadata?: SlideMetadata
  data: TheoryProofData
}

export interface ProcessFlowSlide {
  layout: 'process_flow'
  metadata?: SlideMetadata
  data: ProcessFlowData
}

export interface TechDashboardSlide {
  layout: 'tech_dashboard'
  metadata?: SlideMetadata
  data: TechDashboardData
}

export interface MixedTwoColumnSlide {
  layout: 'mixed_two_column'
  metadata?: SlideMetadata
  data: MixedTwoColumnData
}

export type PPTSlide =
  | CoverSlide
  | AgendaSlide
  | LayerStackSlide
  | TheoryProofSlide
  | ProcessFlowSlide
  | TechDashboardSlide
  | MixedTwoColumnSlide

export interface PPTDocument {
  template_id: ThemeType
  topic: string
  author?: string
  date?: string
  slides: PPTSlide[]
}
