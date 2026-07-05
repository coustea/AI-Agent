export type VisualizerType =
  | '1D_ARRAY'
  | 'TREE'
  | 'GRAPH'
  | 'DP_TABLE'
  | 'LINKED_LIST'
  | 'array'
  | 'graph'
  | 'tree'
  | 'linked-list'
  | 'stack-queue'
  | 'dp-table'
  | 'number-line'
  | 'memory-block'
  | 'process-schedule'

export type ActionType =
  // 通用
  | 'INIT'
  | 'CLEAR'
  // 数组特有
  | 'SWAP'
  | 'COMPARE'
  | 'SET_VALUE'
  // 树/图特有
  | 'ADD_NODE'
  | 'ADD_EDGE'
  | 'VISIT_NODE'
  | 'LEAVE_NODE'
  // DP表特有
  | 'UPDATE_CELL'
  | 'READ_CELL'
  // 原有小写动作兼容
  | 'init'
  | 'compare'
  | 'swap'
  | 'highlight'
  | 'visit'
  | 'move'
  | 'update'
  | 'delete'
  | 'insert'
  | 'push'
  | 'pop'
  | 'enqueue'
  | 'dequeue'
  | 'highlight-edge'
  | 'mark-answer'
  | 'reset'

export type VisualStepType = ActionType | string

export interface VisualizationResponse {
  visualizerType: VisualizerType
  actions: TraceAction[]
}

export interface TraceAction {
  type: ActionType
  payload?: any
}

export type CodeLanguage =
  | 'javascript'
  | 'typescript'
  | 'python'
  | 'java'
  | 'cpp'
  | 'c'

export interface VisualStep {
  id: string
  type: VisualStepType
  targets: string[]
  description: string
  codeLine?: number
  duration?: number
  variables?: Record<string, unknown>
  payload?: Record<string, unknown>
}

export interface ArrayVisualizerState {
  array: number[]
}

export interface VisualizerPayload<TState = unknown> {
  title: string
  visualizerType: VisualizerType
  language: CodeLanguage
  code: string
  input: string
  initialState: TState
  steps: VisualStep[]
  finalState?: TState
  summary?: string
}

export interface PlaybackState {
  playing: boolean
  currentStepIndex: number
  speed: number
  finished: boolean
}

export interface VisualizerGenerationParams {
  language: CodeLanguage
  code: string
  input: string
}
