/** TraceEvent domain — 当前阶段只用 data_structure */
export type TraceDomain = 'data_structure'

/** 可视化器类型 — 小写 kebab-case */
export type VisualizerType =
  | 'array'
  | 'stack-queue'
  | 'linked-list'
  | 'tree'
  | 'graph'
  | 'dp-table'

/** 支持的代码语言 */
export type CodeLanguage = 'python' | 'c' | 'cpp' | 'java' | 'javascript'

/** TraceEvent 事件协议 — 所有语言统一输出 */
export interface TraceEvent {
  id: string
  step: number
  domain: TraceDomain
  visualizerType: VisualizerType
  type: string
  line?: number
  state: TraceEventState
  targets?: Array<string | number>
  message?: string
  formula?: string
}

/** TraceEvent 中的状态快照 */
export interface TraceEventState {
  structure: Record<string, unknown>
  variables?: Record<string, unknown>
  auxiliary?: Record<string, unknown>
}

/** 算法信息 (来自 GET /algorithms) */
export interface AlgorithmInfo {
  key: string
  name: string
  domain: TraceDomain
  visualizerType: VisualizerType
  difficulty: 'easy' | 'medium' | 'hard'
  supportedLanguages: CodeLanguage[]
}

/** 语言信息 (来自 GET /languages) */
export interface LanguageInfo {
  key: CodeLanguage
  label: string
  extension: string
}

/** 模板数据 (来自 GET /templates) */
export interface TemplateData {
  domain: TraceDomain
  algorithm: string
  visualizerType: VisualizerType
  language: CodeLanguage
  templateCode: string
  defaultData: Record<string, unknown>
}

/** 运行结果 (来自 POST /run 成功) */
export interface RunResult {
  domain: TraceDomain
  algorithm: string
  visualizerType: VisualizerType
  language: CodeLanguage
  events: TraceEvent[]
  result: unknown
  summary: string
}

/** 运行错误 (来自 POST /run 失败) */
export interface RunError {
  errorType:
    | 'compile_error'
    | 'runtime_error'
    | 'timeout'
    | 'no_events'
    | 'unsupported_language'
    | 'unsupported_algorithm'
  message: string
  details?: string
}

/** 播放状态 */
export interface PlaybackState {
  playing: boolean
  currentStepIndex: number
  speed: number
  finished: boolean
}
