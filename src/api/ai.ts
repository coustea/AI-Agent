import http from '@/utils/http'
import type { ApiResponse } from '@/api/auth'

// ==========================================
// 类型定义
// ==========================================

export interface ProfileData {
  knowledge_level: string | null
  knowledge_level_score: number | null
  cognitive_style: string | null
  cognitive_style_score: number | null
  error_pattern: string | null
  error_pattern_score: number | null
  learning_goal: string | null
  learning_goal_score: number | null
  learning_history: string | null
  learning_history_score: number | null
  interest_preference: string | null
  interest_preference_score: number | null
  learning_pace: string | null
  learning_pace_score: number | null
  cognitive_level: string | null
  cognitive_level_score: number | null
  profile_summary: string | null
  updated_at: string | null
}

export interface ProfileHistoryItem {
  version: number
  knowledge_level: string | null
  knowledge_level_score: number | null
  cognitive_style: string | null
  cognitive_style_score: number | null
  error_pattern: string | null
  error_pattern_score: number | null
  learning_goal: string | null
  learning_goal_score: number | null
  learning_history: string | null
  learning_history_score: number | null
  interest_preference: string | null
  interest_preference_score: number | null
  learning_pace: string | null
  learning_pace_score: number | null
  cognitive_level: string | null
  cognitive_level_score: number | null
  profile_summary: string | null
  change_reason: string | null
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
  knowledge_level: string | null
  eta_days: number
  confidence: number
}

export interface PathPlanInsights {
  adjustment_reason: string
  next_action: string
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

export function recordLearningEvent(payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/events', payload)
}

export function getEvaluationSummary(limit = 100) {
  return http.get<ApiResponse<EvaluationSummary>>('/ai/evaluation/summary', {
    params: { limit },
  })
}

// ==========================================
// 画像 API
// ==========================================

export function getProfile(userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}` : '/ai/profile'
  return http.get<{ code: number; message: string; data: ProfileData }>(path)
}

export function getProfileHistory(limit = 20, userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}/history` : '/ai/profile/history'
  return http.get<{ code: number; message: string; data: ProfileHistoryItem[] }>(path, {
    params: { limit }
  })
}
