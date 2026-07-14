// 路径节点内可生成的辅助资源类型
export type PathResourceType = 'mindmap' | 'code' | 'reading' | 'ppt' | 'cartoon'
export type PathResourceStatus = 'generating' | 'completed' | 'failed'

// ======================================================================
// 路径偏好参数（前后端对齐）
// ======================================================================

export type LearningScene = 'general' | 'exam' | 'beginner' | 'project' | 'interview'
export type LearningPace = 'slow' | 'normal' | 'fast'
export type LearningGranularity = 'coarse' | 'standard' | 'fine'
export type LearningFocus = 'foundation' | 'key_points' | 'practice' | 'weakness'

/**
 * 学习路径偏好参数 — 前后端对齐的结构化配置
 */
export interface PathPreferences {
  /** 是否融合学习者画像 */
  use_profile: boolean
  /** 学习场景 */
  scene: LearningScene
  /** 学习节奏 */
  pace: LearningPace
  /** 路径粒度 */
  granularity: LearningGranularity
  /** 规划重点列表 */
  focus: LearningFocus[]
}

// ======================================================================
// 请求/响应模型
// ======================================================================

// 路径的阶段结构（如：基础篇 → 进阶篇 → 实战篇）
export interface LearningPathStage {
  stage_id: string
  title: string
}

// 路径的单个学习节点：包含状态流转和前置依赖关系
export interface LearningPathNode {
  id: number
  node_id: string
  stage_id: string
  title: string
  // 状态流转：locked → available → in_progress → (completed | completed_with_gaps)
  status: 'locked' | 'available' | 'in_progress' | 'completed' | 'completed_with_gaps'
  priority: number       // 阶段内排序优先级
  attempt_count: number   // 已学习轮次
  difficulty: string | null
  prerequisites: string[] // 前置节点 node_key 列表
}

// 路径概览：包含 stages + nodes 树形结构，用于路径总览页面
export interface PathOverview {
  id: number
  module: string
  title: string
  goal: string
  topic: string | null
  overall_progress: number
  status: string
  current_node_key: string | null
  stages: LearningPathStage[]
  nodes: LearningPathNode[]
  created_at: string
  updated_at: string
}

// 路径历史记录列表项：概览中的缩略信息
export interface LearningPathHistoryItem {
  id: number
  title: string
  goal: string
  topic: string | null
  overall_progress: number
  status: string
  updated_at: string
}

// 节点教程：primary(首次生成)
export interface LearningPathTutorial {
  id: number
  tutorial_type: 'primary' | string
  version_no: number           // 递增版本号，每次重新生成 +1
  based_on_tutorial_id: number | null  // 基于哪个旧版本生成的
  title: string
  summary: string | null
  content_markdown: string     // 教程正文（Markdown 格式）
  knowledge_points: string[]   // 覆盖的知识点列表
  weak_knowledge_points: string[]  // 薄弱点（用于记录测验中暴露的问题）
  created_at: string
}

// 辅助资源（思维导图/代码/PPT/阅读/动画讲解）
export interface LearningPathResource {
  id: number
  resource_type: PathResourceType | string
  version_no: number
  title: string
  content_format: string      // markdown / json / html 等
  content_text: string | null
  content_json: Record<string, unknown> | null
  summary: string | null
  status: PathResourceStatus
  error_message: string | null
  input_data: Record<string, unknown> | null
  metadata: Record<string, unknown>
  created_at: string
}

// 节点测验题目（每轮固定 5 道选择题）
export interface LearningPathQuestion {
  id: number
  question_no: number
  round_no: number
  mode: string
  type: string
  question: string
  choice: Record<string, string>  // {A: "...", B: "...", C: "...", D: "..."}
  answer: string                   // 正确答案（如 "A"）
  response: string | null          // 用户的作答
  analysis: string | null
  knowledge_points: string[]
  is_correct: boolean | null
}

// 节点学习空间：页面加载时一次性获取的完整状态
export interface LearningPathWorkspace {
  path: PathOverview
  node: LearningPathNode
  current_tutorial: LearningPathTutorial | null  // 当前要展示的教程（最新版本）
  tutorials: LearningPathTutorial[]               // 该节点所有历史/版本的教程
  resources: LearningPathResource[]               // 辅助资源列表
  current_round: number
  quiz_available: boolean
}

// 节点测验轮次：每次生成返回 5 道题
export interface PathQuizRound {
  node_id: number
  tutorial_id: number | null
  round_no: number
  questions: LearningPathQuestion[]
}

export interface PathResourceTaskResponse {
  resource: PathResourceDetail
  run_id: string
}

export type PathResourceEventName = 'resource.started' | 'resource.running' | 'resource.completed' | 'resource.failed'

export interface PathResourceEvent {
  sequence: number
  run_id: string
  path_id: number
  event: PathResourceEventName
  stage: string
  message: string
  progress: number | null
  data: Record<string, unknown>
  timestamp: number
}

// 单题作答
export interface PathQuizAnswerItem {
  question_id: number
  response: string
}

// 提交 5 道题的答案
export interface PathQuizSubmitRequest {
  answers: PathQuizAnswerItem[]
}

// 判分结果：outcome 决定节点状态的下一步流转
export interface PathQuizSubmitResponse {
  node_id: number
  round_no: number
  score: number
  passed: boolean
  outcome: 'completed' | 'completed_with_gaps'
  weak_knowledge_points: string[]
  next_node_id: number | null        // 指向下一节点 ID
  current_tutorial_id: number | null
}

// 创建路径时的表单请求体
export interface PathRequest {
  goal: string
  topic: string
  current_knowledge: string[]
  preferences: PathPreferences
}

// 创建路径的即时响应（完整规划异步通过 SSE 返回）
export interface CreatePathResponse {
  id: number
  run_id: string   // SSE 事件流的 run_id，前端用此建立 EventSource 连接
  status: string
}

// 从学习画像模块聚合的用户学习信号快照
interface LearningSignalSnapshot {
  average_score: number | null
  weak_topics: string[]
  preferred_resources: string[]
  negative_feedback: string[]
  completed_resource_count: number
  viewed_resource_count: number
  active_minutes: number
  recommendations: string[]
}

// 路径学习评估：后端根据学习画像+路径进度生成
export interface PathLearningEvaluationResponse {
  path_id: number
  overall_progress: number
  current_node_key: string | null
  signal_snapshot: LearningSignalSnapshot
  needs_optimization: boolean
  optimization_tips: string[]
}

// 资源任务和工作区返回同一份辅助资源结构。
export type PathResourceDetail = LearningPathResource
