import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'

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

// 获取首页推荐卡片数据（冷启动/活跃态）
export function getRecommendation() {
  return http.get<ApiResponse<RecommendationData>>('/ai/dashboard/recommendation')
}

// ---------------------------------------------------------------------------
// 2. Profile Radar
// ---------------------------------------------------------------------------

export interface ProfileRadarData {
  score: number | null
  dimensions?: { key: string; label: string; score: number }[]
  weak_areas?: string[]
  metrics: {
    dimension_scores?: Record<string, number>
  }
  radar: {
    path: string
    note: string
  }
}

// 获取用户能力画像雷达图数据
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

// 获取继续学习列表（进行中的学习路径）
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
}

// 获取快捷操作列表
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

// 获取最近生成的资源列表
export function getRecentResources() {
  return http.get<ApiResponse<RecentResourceItem[]>>('/ai/dashboard/recent-resources')
}

// ---------------------------------------------------------------------------
// 6. Profile Study Snapshot Compatibility
// ---------------------------------------------------------------------------

export interface StudyStatsData {
  weekly_days: number
}

// 个人中心旧看板仍需要本周活跃天数。后端旧 study-stats 路由已移除，
// 这里优先从 7 天学习评估事实快照中读取活跃天数，避免重新引入旧接口。
export async function getStudyStats() {
  const history = await http.get<ApiResponse<{
    items: {
      id: number
      range_days: number
      status: string
    }[]
  }>>(
    '/ai/evaluation/reports',
    { params: { page: 1, page_size: 50 } },
  )
  const weeklyReport = history.data.data.items.find(
    item => item.status === 'ready' && item.range_days === 7,
  )
  const response = weeklyReport
    ? await http.get<ApiResponse<{ facts_snapshot?: { activity?: { active_days?: number } } }>>(
      `/ai/evaluation/reports/${weeklyReport.id}`,
    )
    : await http.get<ApiResponse<{ facts_snapshot?: { activity?: { active_days?: number } } } | null>>(
      '/ai/evaluation/reports/latest',
    )

  return {
    ...response,
    data: {
      ...response.data,
      data: {
        weekly_days: response.data.data?.facts_snapshot?.activity?.active_days ?? 0,
      },
    },
  }
}
