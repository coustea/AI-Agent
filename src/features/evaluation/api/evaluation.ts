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
  daily_breakdown: { date: string; seconds: number }[]
}

export interface DashboardLoginActivity {
  active_days: number
}

export interface DashboardFeatureUsage {
  key: 'quiz' | 'chat' | 'path' | 'resource'
  name: string
  count: number
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
  login_activity: DashboardLoginActivity
  feature_usage: DashboardFeatureUsage[]
  evaluation_summary: DashboardEvaluationSummary
  practice_chart: DashboardPracticeChart
  learning_path: DashboardLearningPath
  module_time_breakdown: DashboardModuleTime[]
  latest_assessment: DashboardLatestAssessment | null
  guidance_strategy: Record<string, any>
  window: DashboardWindow
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
