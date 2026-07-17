import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  LearningEventCreate,
  LearningSessionCreate,
} from '@/features/evaluation/model/evaluation'

export type {
  LearningEventCreate,
  LearningSessionCreate,
}

// ── 看板数据结构（与后端 GET /evaluation/dashboard 对齐）────────────────────────

export interface DashboardTimeStats {
  total_seconds: number
  today_seconds: number
  streak_days: number
  daily_breakdown: { date: string; seconds: number }[]
  context_breakdown: Record<string, number>
}

export interface DashboardEvaluationSummary {
  completed_resources: number
  viewed_resources: number
  generated_resources: number
  event_count: number
  weak_topics: string[]
  focus_topics: string[]
  recommendations: string[]
}

export interface DashboardPracticeTopic {
  topic: string
  accuracy: number
  submitted: number
  correct: number
}

export interface DashboardPracticeChart {
  overall_accuracy: number
  total_submitted: number
  total_correct: number
  by_topic: DashboardPracticeTopic[]
}

export interface DashboardLearningPath {
  nodes_started: number
  nodes_completed: number
  completion_rate: number
}

export interface DashboardLatestAssessment {
  id: number
  assessment: string
  generated_at: string
}

export interface DashboardWindow {
  days: number
  start: string
  end: string
}

export interface DashboardModuleTime {
  module: string
  seconds: number
}

export interface DashboardData {
  time_stats: DashboardTimeStats
  evaluation_summary: DashboardEvaluationSummary
  practice_chart: DashboardPracticeChart
  learning_path: DashboardLearningPath
  module_time_breakdown: DashboardModuleTime[]
  latest_assessment: DashboardLatestAssessment | null
  guidance_strategy: Record<string, any>
  window: DashboardWindow
}

// ── 旧类型兼容（供 Profile.vue 等现有组件平滑迁移）──────────────────────────────

export interface LearningTimeStats {
  total_seconds: number
  today_seconds: number
  streak_days: number
  daily_breakdown: { date: string; seconds: number }[]
  context_breakdown: Record<string, number>
}

export interface EvaluationSummary {
  completed_resources: number
  viewed_resources: number
  event_count: number
  weak_topics: string[]
  focus_topics: string[]
  recommendations: string[]
}

// ── API 函数 ────────────────────────────────────────────────────────────────────

// 记录学习事件（答题/浏览等）
export function recordLearningEvent(payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number; deduplicated: boolean }>>('/ai/evaluation/events', payload)
}

// 记录学习会话（单次学习时长）
export function recordLearningSession(payload: LearningSessionCreate) {
  return http.post<ApiResponse<{ id: number; deduplicated: boolean }>>('/ai/evaluation/sessions', payload)
}

// 记录学习路径相关事件（关联 pathId）
export function recordPathLearningEvent(pathId: number, payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>(`/ai/path-plan/${pathId}/events`, payload)
}

// 获取看板数据（新端点，一次请求返回全部图表数据）
export function getDashboard(rangeDays: number = 7) {
  return http.get<ApiResponse<DashboardData>>('/ai/evaluation/dashboard', {
    params: { range_days: rangeDays },
  })
}

// ── 旧函数兼容层 ───────────────────────────────────────────────────────────────
// Profile.vue 现有调用 getLearningTimeStats / getEvaluationSummary，
// 这两个函数内部改为调用新 dashboard 端点，返回格式不变，实现零改动迁移。

let _cachedDashboard: DashboardData | null = null
let _cachedRangeDays: number | null = null

async function _ensureDashboard(days: number): Promise<DashboardData> {
  if (_cachedDashboard && _cachedRangeDays === days) {
    return _cachedDashboard
  }
  const response = await getDashboard(days)
  _cachedDashboard = response.data.data
  _cachedRangeDays = days
  return _cachedDashboard!
}

export async function getLearningTimeStats(days = 7) {
  const dashboard = await _ensureDashboard(days)
  return {
    data: {
      code: 200,
      message: 'success',
      data: dashboard.time_stats,
    },
  }
}

export async function getEvaluationSummary(_limit = 100) {
  const dashboard = await _ensureDashboard(7)
  const summary = dashboard.evaluation_summary
  return {
    data: {
      code: 200,
      message: 'success',
      data: {
        completed_resources: summary.completed_resources,
        viewed_resources: summary.viewed_resources,
        event_count: summary.event_count,
        weak_topics: summary.weak_topics,
        focus_topics: summary.focus_topics,
        recommendations: summary.recommendations,
      },
    },
  }
}
