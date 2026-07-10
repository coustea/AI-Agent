// 可视化器类型 — 小写 kebab-case
export type VisualizerType =
  | 'array'
  | 'stack-queue'
  | 'linked-list'
  | 'tree'
  | 'graph'
  | 'dp-table'

// 支持的代码语言
export type CodeLanguage = 'python' | 'c' | 'cpp' | 'java' | 'javascript'

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
  defaultData: Record<string, unknown>
  requiredEvents: string[]
  supportedLanguages: CodeLanguage[]
}

// 运行结果 (来自 POST /run 成功)
export interface RunResult {
  domain: string
  algorithm: string
  visualizerType: VisualizerType
  language: CodeLanguage
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
    | 'COMPILE_ERROR'
    | 'RUNTIME_ERROR'
    | 'TIMEOUT'
    | 'TRACE_FILE_MISSING'
    | 'TRACE_JSON_INVALID'
    | 'TRACE_EVENT_EMPTY'
    | 'TRACE_EVENT_INVALID'
    | 'TRACE_VISUALIZER_TYPE_INVALID'
    | 'RUNTIME_NOT_FOUND'
    | 'TRACER_SDK_MISSING'
    | 'VISUALIZER_RUN_ERROR'
  message: string
  details?: string
}
