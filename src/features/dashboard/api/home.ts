import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type { ProfileScoreData } from '@/features/profile/api/profile'

// ---------------------------------------------------------------------------
// 1. Recommendation
// ---------------------------------------------------------------------------

export interface RecommendationData {
  state: 'cold_start' | 'active'
  recommendation: {
    label: string
    title: string
    text: string
    action: string
    path: string
    icon: string
  }
}

export function getRecommendation() {
  return http.get<ApiResponse<RecommendationData>>('/ai/dashboard/recommendation')
}

// ---------------------------------------------------------------------------
// 2. Profile Radar
// ---------------------------------------------------------------------------

export interface ProfileRadarData extends ProfileScoreData {
  weak_areas?: string[]
  radar: {
    eyebrow: string
    title: string
    link_label: string
    path: string
    note: string
  }
}

export function getProfileRadar() {
  return http.get<ApiResponse<ProfileRadarData>>('/ai/dashboard/profile-radar')
}

// ---------------------------------------------------------------------------
// 3. Continue Learning
// ---------------------------------------------------------------------------

export interface ContinueLearningData {
  active_paths: {
    id: number
    title: string
    overall_progress: number
    current_node_title: string | null
    current_node_id: string | null
    updated_at: string | null
    last_learned_at: string | null
  }[]
}

export function getContinueLearning() {
  return http.get<ApiResponse<ContinueLearningData>>('/ai/dashboard/continue-learning')
}

// ---------------------------------------------------------------------------
// 4. Quick Actions
// ---------------------------------------------------------------------------

export interface HomeActionItem {
  label: string
  description: string
  tag?: string
  path: string
  icon: string
}

export interface QuickActionsData {
  actions: HomeActionItem[]
  today_suggestions: {
    title: string
    reason: string
    path: string
    tone: string
  }[]
}

export function getQuickActions() {
  return http.get<ApiResponse<QuickActionsData>>('/ai/dashboard/quick-actions')
}

// ---------------------------------------------------------------------------
// 5. Recent Resources
// ---------------------------------------------------------------------------

export interface RecentResourceItem {
  id: number
  title: string
  type: string
  agent: string
  created_at: string | null
}

export function getRecentResources() {
  return http.get<ApiResponse<RecentResourceItem[]>>('/ai/dashboard/recent-resources')
}

// ---------------------------------------------------------------------------
// 6. Daily Challenge
// ---------------------------------------------------------------------------

export interface DailyChallengeData {
  id: string
  subject: string
  content: string
  difficulty: string | null
  type: string
  estimated_minutes: number
  source: string
  reason: string
}

export function getDailyChallenge() {
  return http.get<ApiResponse<DailyChallengeData | null>>('/ai/dashboard/daily-challenge')
}

// ---------------------------------------------------------------------------
// 7. Study Stats
// ---------------------------------------------------------------------------

export interface StudyStatsData {
  weekly_days: number
  total_hours: number
  pending_nodes: number
  today_suggestions: number
}

export function getStudyStats() {
  return http.get<ApiResponse<StudyStatsData>>('/ai/dashboard/study-stats')
}
