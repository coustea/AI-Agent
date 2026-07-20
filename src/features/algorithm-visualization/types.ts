// 可视化器类型 — 小写 kebab-case
export type VisualizerType =
  | 'array'
  | 'stack-queue'
  | 'linked-list'
  | 'tree'
  | 'graph'
  | 'dp-table'

// TraceEvent 事件协议 — 所有语言统一输出
export interface TraceEvent {
  id: string
  step: number
  visualizerType: VisualizerType
  type: string
  line?: number
  state: TraceEventState
  targets?: Array<string | number>
  message?: string
  formula?: string
}

// TraceEvent 中的状态快照
export interface TraceEventState {
  structure: Record<string, unknown>
  auxiliary?: Record<string, unknown>
}

export interface VisualEdge {
  to: string
  weight?: string | number
  constructed?: boolean
}

export interface VisualNode {
  id: string
  label: string
  tone?: string
  next?: string | null
  left?: string
  right?: string
  children?: string[]
  distance?: string | number
  edges?: VisualEdge[]
  x?: number
  y?: number
}

export interface VisualPointer {
  label: string
  nodeId?: string
  nodeIndex?: number
  itemIndex?: number
  tone?: string
}

export interface HighlightedCell {
  row: number
  col: number
  tone: 'active' | 'dependency' | 'success'
}

// 算法信息 (来自 GET /algorithms)
export interface AlgorithmInfo {
  key: string
  name: string
  domain: string
  visualizerType: VisualizerType
  difficulty: 'easy' | 'medium' | 'hard'
}

// 模板数据 (来自 GET /templates/{templateKey})
export interface TemplateData {
  key: string
  name: string
  domain: string
  visualizerType: VisualizerType
  difficulty: AlgorithmInfo['difficulty']
  version: string
  templateCode: string
  defaultInput: Record<string, unknown>
  inputSchema: InputSchema
}

export interface InputSchema {
  type?: 'object' | 'array' | 'string' | 'boolean' | 'integer' | 'number' | 'null'
  required?: string[]
  properties?: Record<string, InputSchema>
  items?: InputSchema
}

// 运行结果 (来自 POST /templates/{templateKey}/runs 成功)
export interface RunResult {
  templateKey: string
  templateVersion: string
  visualizerType: VisualizerType
  events: TraceEvent[]
  result: unknown
  summary: string
  stdout?: string
}

// 运行错误 (来自 POST /run 失败)
export interface RunError {
  errorType:
    | 'MISSING_ALGORITHM'
    | 'RUNTIME_ERROR'
    | 'VISUALIZER_RUN_ERROR'
    | 'INPUT_INVALID'
    | 'TRACE_EVENT_EMPTY'
  message: string
  details?: string
}
