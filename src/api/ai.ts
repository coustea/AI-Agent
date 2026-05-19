import http from '@/utils/http'
import type { ApiResponse } from '@/api/auth'

// ==========================================
// 类型定义
// ==========================================

export interface ProfileData {
  user_id: number | null
  module: string | null
  profile_markdown: string | null
  profile_json: Record<string, unknown> | null
  profile_score_json: Record<string, unknown> | null
  version: number | null
  confidence: number | null
  source_session_ids: string[] | null
  source_summary_ids: number[] | null
  source_event_ids: number[] | null
  updated_reason: string | null
  updated_at: string | null
}

export interface StudentProfileData {
  education_level: string | null
  grade: string | null
  major: string | null
  courses: string[]
  learning_goal: string | null
  school: string | null
  school_level: string | null
  preferred_language: string | null
  cognitive_style?: string | null
  interaction_preference?: string | null
  practice_ability?: string | null
  weakness_points?: string[] | null
}

export interface ProfileOnboardingData {
  student_profile: StudentProfileData
  profile_initialized: boolean
}

export interface ProfileOnboardingUpdate {
  education_level: string
  grade: string
  major: string
  courses: string[]
  learning_goal: string
  school?: string | null
  school_level?: string | null
  preferred_language?: string | null
  cognitive_style?: string | null
  interaction_preference?: string | null
  practice_ability?: string | null
  weakness_points?: string[] | null
}

export interface ProfileOnboardingUpdateResult {
  profile: ProfileData
  onboarding: ProfileOnboardingData
}

export interface ProfileScoreData {
  user_id: number | null
  module: string | null
  version: number | null
  score: number | null
  confidence: number | null
  metrics: {
    dimension_scores?: Record<string, number | null>
    section_coverage?: number | null
    evidence_quality?: number | null
    uncertainty_handling?: number | null
    content_richness?: number | null
  }
  missing_sections: string[]
  scored_at: string | null
  updated_at: string | null
}

export interface ProfileHistoryItem {
  id: number
  user_id: number
  module: string
  version: number
  profile_json: Record<string, unknown> | null
  profile_score_json: Record<string, unknown> | null
  change_reason: string | null
  source_session_ids: string[] | null
  source_summary_ids: number[] | null
  source_event_ids: number[] | null
  created_at: string | null
}


export type PathNodeStatus = 'success' | 'processing' | 'wait'
export type PathStageStatus = PathNodeStatus

export interface PathNode {
  id: string
  title: string
  status: PathNodeStatus
  progress: number
  priority: number
  desc: string | null
  recommendation_reason?: string | null
  resource_id?: number | null
  resource_item_id?: number | null
  resource_type?: string | null
  resource_title?: string | null
  resource_summary?: string | null
  resource_format?: string | null
  resource_status?: 'available' | 'missing' | 'pending' | 'failed' | null
}

export interface PathStage {
  id: string
  title: string
  status: PathStageStatus
  progress: number
  nodes: PathNode[]
}

export interface PathPlanSummary {
  overall_progress: number
  current_stage: string | null
  current_node?: string | null
  knowledge_level: string | null
  eta_days: number
  confidence: number
}

export interface PathRecommendedNode {
  node_id: string
  title: string
  priority: number
  stage_id: string
  reason: string
}

export interface PathPlanInsights {
  adjustment_reason: string
  next_action: string
  recommended_nodes?: PathRecommendedNode[]
}

export interface PathPlanMeta {
  generated_at: string
  data_sources: string[]
  resource_id: number | null
  plan_version: number
}

export interface PathPlan {
  summary: PathPlanSummary
  stages: PathStage[]
  insights: PathPlanInsights
  meta: PathPlanMeta
}

export interface PathPlanFeedbackParams {
  feedback: string
  weak_points?: string[]
  resource_id?: number | null
}

export function getPathPlan(resourceId?: number) {
  return http.get<{ code: number; message: string; data: PathPlan }>('/ai/path-plan', {
    params: resourceId ? { resource_id: resourceId } : undefined,
  })
}

export function rebuildPathPlan(resourceId?: number) {
  return http.post<{ code: number; message: string; data: PathPlan }>('/ai/path-plan/rebuild', {
    resource_id: resourceId ?? null,
  })
}

export function applyPathFeedback(params: PathPlanFeedbackParams) {
  return http.post<{ code: number; message: string; data: PathPlan }>('/ai/path-plan/feedback', params)
}

// ==========================================
// 学习效果评估 API
// ==========================================

export type LearningEventType =
  | 'resource_viewed'
  | 'resource_completed'
  | 'quiz_submitted'
  | 'path_feedback'
  | 'tutor_helpful'
  | 'resource_feedback'
  | 'learning_heartbeat'

export interface LearningEventCreate {
  event_type: LearningEventType
  session_id?: string | null
  resource_id?: number | null
  course?: string | null
  topic?: string | null
  score?: number | null
  duration_seconds?: number | null
  feedback?: string | null
  metadata?: Record<string, unknown>
}

export interface LearningEventItem {
  id: number
  event_type: string
  course: string | null
  topic: string | null
  score: number | null
  duration_seconds: number | null
  feedback: string | null
  created_at: string
}

export interface EvaluationMetric {
  label: string
  value: string
  trend: string
}

export interface EvaluationSummary {
  event_count: number
  average_score: number | null
  completed_resources: number
  viewed_resources: number
  active_minutes: number
  weak_topics: string[]
  preferred_resources: string[]
  recommendations: string[]
  metrics: EvaluationMetric[]
  recent_events: LearningEventItem[]
}

export interface DailyTimeEntry {
  date: string
  seconds: number
}

export interface HourlyDistributionEntry {
  hour: number
  seconds: number
}

export interface LearningTimeStats {
  today_seconds: number
  week_seconds: number
  month_seconds: number
  total_seconds: number
  streak_days: number
  daily_breakdown: DailyTimeEntry[]
  hourly_distribution: HourlyDistributionEntry[]
  context_breakdown?: Record<string, number>
}

export function recordLearningEvent(payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/events', payload)
}

export function getEvaluationSummary(limit = 100) {
  return http.get<ApiResponse<EvaluationSummary>>('/ai/evaluation/summary', {
    params: { limit },
  })
}

export function getLearningTimeStats(days = 30) {
  return http.get<ApiResponse<LearningTimeStats>>('/ai/evaluation/time-stats', {
    params: { days },
  })
}

// ==========================================
// 画像 API
// ==========================================

export function getProfile(userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}` : '/ai/profile'
  return http.get<{ code: number; message: string; data: ProfileData }>(path)
}

export function getProfileScore(userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}/score` : '/ai/profile/score'
  return http.get<{ code: number; message: string; data: ProfileScoreData }>(path)
}

export function getProfileOnboarding() {
  return http.get<ApiResponse<ProfileOnboardingData>>('/ai/profile/onboarding')
}

export function updateProfileOnboarding(payload: ProfileOnboardingUpdate) {
  return http.patch<ApiResponse<ProfileOnboardingUpdateResult>>('/ai/profile/onboarding', payload)
}

export function getProfileHistory(limit = 20, userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}/history` : '/ai/profile/history'
  return http.get<{ code: number; message: string; data: ProfileHistoryItem[] }>(path, {
    params: { limit }
  })
}

// ==========================================
// 资源生成历史 API
// ==========================================

export interface GeneratedResourceItem {
  id: number
  learning_need: string | null
  status: string
  resource_types: string[]
  created_at: string | null
  updated_at: string | null
}

export interface ResourceItemDetail {
  id: number
  type: string
  title: string
  format: string
  content: string | null
  summary: string
  summary_data: Record<string, unknown>
  metadata: Record<string, unknown>
  status: string
  error_message: string | null
  created_at: string | null
  updated_at: string | null
}

export interface GeneratedResourceBundle {
  id: string
  task_id: string
  title: string
  learning_need: string
  selected_agents: string[]
  resources: ResourceItemDetail[]
  study_path: unknown[]
  review_result: unknown
  status: string
  created_at: string | null
  updated_at: string | null
  metadata: Record<string, unknown>
}

export function getGeneratedResources(limit = 20) {
  return http.get<ApiResponse<GeneratedResourceItem[]>>('/ai/resources', {
    params: { limit }
  })
}

export function getGeneratedResourceDetail(resourceId: number) {
  return http.get<ApiResponse<GeneratedResourceBundle>>(`/ai/resources/${resourceId}`)
}

// ==========================================
// 学校搜索 API
// ==========================================

export interface SchoolItem {
  id: number
  name: string
  level: string | null
}

export function searchSchools(keyword: string = '', limit = 20) {
  return http.get<ApiResponse<SchoolItem[]>>('/ai/schools/search', {
    params: { keyword, limit }
  })
}
