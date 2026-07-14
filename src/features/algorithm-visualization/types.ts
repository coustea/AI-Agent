// 可视化器类型 — 小写 kebab-case
export type VisualizerType =
  | 'array'
  | 'stack-queue'
  | 'linked-list'
  | 'tree'
  | 'graph'
  | 'dp-table'

// 支持的代码语言
export type CodeLanguage = 'python'

// TraceEvent 事件协议 — 所有语言统一输出
export interface TraceEvent {
  id: string
  step: number
  domain: string
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
  variables?: Record<string, unknown>
  auxiliary?: Record<string, unknown>
}

export interface VisualEdge {
  to: string
  weight?: string | number
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
  supportedLanguages: CodeLanguage[]
}

// 语言信息 (来自 GET /languages)
export interface LanguageInfo {
  key: CodeLanguage
  label: string
  extension: string
}

// 模板数据 (来自 GET /templates)
export interface TemplateData {
  domain: string
  algorithm: string
  visualizerType: VisualizerType
  language: CodeLanguage
  templateCode: string
  requiredEvents: string[]
  supportedLanguages: CodeLanguage[]
  defaultInput: Record<string, unknown>
  inputSchema: InputSchema
}

export interface InputSchema {
  type?: 'object' | 'array' | 'string' | 'boolean' | 'integer' | 'number' | 'null'
  required?: string[]
  properties?: Record<string, InputSchema>
  items?: InputSchema
}

export interface CustomFunctionInfo {
  name: string
  parameters: string[]
}

export interface CustomCodeContract {
  entryFunction: string
  functions: CustomFunctionInfo[]
  inputSchema: InputSchema
  defaultInput: Record<string, unknown>
}

// 运行结果 (来自 POST /run 成功)
export interface RunResult {
  domain: string
  algorithm: string
  visualizerType: VisualizerType
  language: CodeLanguage
  executionMode: 'official' | 'custom'
  events: TraceEvent[]
  result: unknown
  summary: string
  stdout?: string
}

// 运行错误 (来自 POST /run 失败)
export interface RunError {
  errorType:
    | 'MISSING_LANGUAGE'
    | 'MISSING_ALGORITHM'
    | 'MISSING_CODE'
    | 'UNSUPPORTED_ALGORITHM'
    | 'UNSUPPORTED_LANGUAGE'
    | 'VISUALIZER_TYPE_MISMATCH'
    | 'RUNTIME_ERROR'
    | 'TIMEOUT'
    | 'TRACE_FILE_MISSING'
    | 'TRACE_JSON_INVALID'
    | 'TRACE_EVENT_EMPTY'
    | 'TRACE_EVENT_INVALID'
    | 'TRACE_VISUALIZER_TYPE_INVALID'
    | 'TRACER_SDK_MISSING'
    | 'INSTRUMENTATION_FAILED'
    | 'CUSTOM_VISUALIZATION_ERROR'
    | 'CODE_TOO_LARGE'
    | 'MISSING_VISUALIZER_TYPE'
    | 'VISUALIZER_RUN_ERROR'
    | 'INPUT_INVALID'
    | 'CUSTOM_CONTRACT_INVALID'
  message: string
  details?: string
}
