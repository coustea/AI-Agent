// src/types/chat.ts — 聊天相关类型定义

// OpenAI 格式的内容部分类型
interface AttachmentContentMeta {
  url?: string
  file_type?: string
  original_name?: string
  mime_type?: string | null
  size_bytes?: number
}

export type ContentPart =
  | { type: "text"; text: string }
  | ({ type: "image_url"; image_url: { url: string; detail?: "auto" | "low" | "high" } } & AttachmentContentMeta)
  | ({ type: "file"; file: { file_id?: string; file_data?: string; filename?: string } } & AttachmentContentMeta)

export type TeachingDiagramType = 'comparison' | 'flowchart' | 'sequence' | 'framework' | 'summary' | 'hierarchy' | 'tree' | 'grid' | 'protocol' | 'timeline'
type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced'

// ---- 1. 对比图 ----
interface ComparisonEntity {
  name: string
  core_label: string
  short_desc: string
}

interface ComparisonDimension {
  name: string
  left: string
  right: string
  highlight?: boolean | null
}

interface VisualSummary {
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

interface FlowchartNode {
  id: string
  title: string
  short_desc?: string
  type: FlowchartNodeType
}

interface FlowchartEdge {
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
interface SequenceMessage {
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
interface FrameworkModule {
  title: string
  items: string[]
}

export interface FrameworkPayload {
  center: string
  modules: FrameworkModule[]
}

// ---- 5. 总结卡片图 ----
interface SummaryCard {
  title: string
  short_desc: string
}

export interface SummaryPayload {
  cards: SummaryCard[]
}

// ---- 6. 层级概括图 ----
interface HierarchyBranch {
  title: string
  children: string[]
}

export interface HierarchyPayload {
  root: string
  branches: HierarchyBranch[]
}

// ---- 7. 二叉树图 ----
export interface TreeDiagramNode {
  id: string
  label: string
  left_id: string | null
  right_id: string | null
  type?: 'normal' | 'highlight' | 'null' | null
  detail?: string | null
}

export interface TreePayload {
  root_id: string
  nodes: TreeDiagramNode[]
}

// ---- 8. 网格/内存/指针图 ----
export interface GridCell {
  index: string
  label: string
  status: 'normal' | 'active' | 'empty' | 'pointer'
  pointer?: string | null
  detail?: string | null
}

export interface GridPayload {
  layout: 'horizontal' | 'vertical' | 'matrix'
  cols?: number | null
  cells: GridCell[]
}

// ---- 9. 协议字段/报文格式图 ----
export interface ProtocolField {
  name: string
  detail: string
  width_ratio?: number | null
  highlight: boolean
}

export interface ProtocolPayload {
  orientation: 'vertical' | 'horizontal_split'
  fields: ProtocolField[]
}

// ---- 10. 时序轴/时空生命周期图 ----
export interface TimelineBlock {
  label: string
  start: number
  duration: number
  status: 'normal' | 'active' | 'idle' | 'stall'
}

export interface TimelineTrack {
  track_name: string
  blocks: TimelineBlock[]
}

export interface TimelinePayload {
  axis_label: string
  tracks: TimelineTrack[]
}

// ---- 辅助文字 ----
interface TeachingContent {
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
  | TreePayload
  | GridPayload
  | ProtocolPayload
  | TimelinePayload

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

export interface ChatMessageItem {
  id?: number
  user_message_id?: number | null
  role: string
  content: ContentPart[]
  tool_calls?: Array<{ id: string; name: string; args?: Record<string, unknown> }> | null
  tool_call_id?: string | null
  attachment_analyses: Array<{
    id: string
    analysis_type: string
    status: string
    content: string
    error?: string | null
  }>
  activities: Array<{
    activity_id: string
    kind: 'agent' | 'tool' | 'attachment' | 'workflow'
    stage?: string | null
    status: 'running' | 'done' | 'failed'
    title: string
    summary?: string
    message?: string
    detail?: Record<string, unknown>
  }>
  usage_metadata?: Record<string, unknown> | null
  diagram?: TeachingDiagram | null
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
  size_bytes?: number
  mime_type?: string
}

export interface MessageAttachmentInput {
  url: string
  file_type: string
  original_name: string
  size_bytes?: number
  mime_type?: string
}

export interface StreamChatParams {
  message?: string
  session_id?: string
  attachments?: MessageAttachmentInput[]
  need_teaching_diagram?: boolean
  enable_web_search?: boolean
}
