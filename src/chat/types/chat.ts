// src/types/chat.ts — 聊天相关类型定义

export interface AttachmentInfo {
  url: string
  type: string  // "image" | "document"
  name: string
}

export type TeachingDiagramType = 'comparison' | 'flowchart' | 'sequence' | 'framework' | 'summary' | 'hierarchy'
export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced'

// ---- 1. 对比图 ----
export interface ComparisonEntity {
  name: string
  core_label: string
  short_desc: string
}

export interface ComparisonDimension {
  name: string
  left: string
  right: string
  highlight?: string | null
}

export interface VisualSummary {
  left_keyword: string
  right_keyword: string
  center_conclusion: string
}

export interface ComparisonPayload {
  left_entity: ComparisonEntity
  right_entity: ComparisonEntity
  dimensions: ComparisonDimension[]
  visual_summary: VisualSummary
}

// ---- 2. 流程图 ----
export type FlowchartNodeType = 'start' | 'process' | 'decision' | 'end' | 'danger'

export interface FlowchartNode {
  id: string
  title: string
  short_desc?: string
  type: FlowchartNodeType
}

export interface FlowchartEdge {
  from: string
  to: string
  label?: string | null
}

export interface FlowchartPayload {
  direction: 'vertical' | 'horizontal'
  nodes: FlowchartNode[]
  edges: FlowchartEdge[]
}

// ---- 3. 时序图 ----
export interface SequenceMessage {
  from: string
  to: string
  label: string
  detail?: string | null
}

export interface SequencePayload {
  actors: string[]
  messages: SequenceMessage[]
}

// ---- 4. 知识框架图 ----
export interface FrameworkModule {
  title: string
  items: string[]
}

export interface FrameworkPayload {
  center: string
  modules: FrameworkModule[]
}

// ---- 5. 总结卡片图 ----
export interface SummaryCard {
  title: string
  short_desc: string
}

export interface SummaryPayload {
  cards: SummaryCard[]
}

// ---- 6. 层级概括图 ----
export interface HierarchyBranch {
  title: string
  children: string[]
}

export interface HierarchyPayload {
  root: string
  branches: HierarchyBranch[]
}

// ---- 辅助文字 ----
export interface TeachingContent {
  core_explanation: string
  key_points: string[]
  common_mistakes?: string[]
  examples?: string[]
  summary: string
}

// ---- 顶层 TeachingDiagram ----
export type VisualContent =
  | ComparisonPayload
  | FlowchartPayload
  | SequencePayload
  | FrameworkPayload
  | SummaryPayload
  | HierarchyPayload

export interface TeachingDiagram {
  graph_type: TeachingDiagramType
  title: string
  subtitle?: string | null
  teaching_goal: string
  course?: string | null
  difficulty: DifficultyLevel
  visual_content: VisualContent
  teaching_content: TeachingContent
}

export interface KnowledgeSource {
  rank?: number
  source: string
  file_name?: string
  chunk_index?: number
  distance?: number
}

export interface ChatMessageItem {
  role: string
  content: string
  attachments: AttachmentInfo[] | null
  teaching_diagram: TeachingDiagram | null
  created_at: string | null
}

export interface ChatSession {
  id: string
  title: string
  updated_at: string
}

export interface UploadResult {
  url: string
  file_type: string
  original_name: string
  size_bytes: number
}

export interface StreamChatParams {
  message?: string
  history?: StreamChatHistoryItem[]
  session_id?: string
  attachments?: string[]
  need_teaching_diagram?: boolean
  generate_video?: boolean
  enable_web_search?: boolean
  enable_knowledge_base?: boolean
}

export interface StreamChatHistoryItem {
  role: 'user' | 'assistant' | 'ai' | 'system'
  content: string
  attachments?: AttachmentInfo[] | null
  teaching_diagram?: TeachingDiagram | null
}

export interface StreamChatEvent {
  event: string
  data: unknown
}