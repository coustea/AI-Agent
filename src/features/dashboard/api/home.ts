import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type { ProfileScoreData } from '@/features/profile/api/profile'

export interface HomeActionItem {
  label: string
  description: string
  tag?: string
  path: string
  icon: string
}

export interface HomeDashboardData {
  state: 'cold_start' | 'active'
  recommendation: {
    label: string
    title: string
    text: string
    action: string
    path: string
    icon: string
  }
  radar: {
    eyebrow: string
    title: string
    link_label: string
    path: string
    note: string
  }
  quick_section: {
    eyebrow: string
    title: string
    actions: HomeActionItem[]
  }
  recent_modules?: {
    latest_resource: {
      id: number
      title: string
      status: string
      created_at: string
    } | null
    active_path: {
      id: number
      title: string
      overall_progress: number
      current_node_title: string | null
    } | null
    recent_quiz: {
      topic: string
      score: number
      created_at: string
    } | null
    recommended_question?: {
      id: string
      subject: string
      content: string
      difficulty: string | null
      type: string
    } | null
  }
  profile_score: ProfileScoreData | null
}

export function getHomeDashboard() {
  return http.get<ApiResponse<HomeDashboardData>>('/ai/dashboard/home')
}
