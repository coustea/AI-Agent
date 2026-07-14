import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  LearningEventCreate,
  LearningSessionCreate,
} from '@/features/evaluation/model/evaluation'
import type {
  AssessmentFacts,
  GuidanceStrategyResponse,
  LearningAssessmentReport,
  ReportsHistoryResponse,
} from '@/features/learning-assessment/model/assessment'

export type {
  LearningEventCreate,
  LearningSessionCreate,
}

export interface LearningTimeStats {
  total_seconds: number
  today_seconds: number
  streak_days: number
  daily_breakdown: { date: string; seconds: number }[]
  // 最新评估事实快照中的模块事件次数，用于个人中心“功能使用占比”。
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

async function getReportForRange(rangeDays?: 7 | 14 | 30): Promise<LearningAssessmentReport | null> {
  if (rangeDays) {
    const history = await http.get<ApiResponse<ReportsHistoryResponse>>('/ai/evaluation/reports', {
      params: { page: 1, page_size: 50 },
    })
    const matched = history.data.data.items.find(
      item => item.status === 'ready' && item.range_days === rangeDays,
    )
    if (matched) {
      const detail = await http.get<ApiResponse<LearningAssessmentReport>>(`/ai/evaluation/reports/${matched.id}`)
      return detail.data.data
    }
  }

  const response = await http.get<ApiResponse<LearningAssessmentReport | null>>('/ai/evaluation/reports/latest')
  return response.data.data ?? null
}

async function getLatestFacts(rangeDays?: 7 | 14 | 30): Promise<AssessmentFacts | null> {
  const report = await getReportForRange(rangeDays)
  return report?.facts_snapshot ?? null
}

function moduleToProfileContext(module: string): string {
  const map: Record<string, string> = {
    chat: 'Tutor',
    quiz: 'QuestionBank',
    path: 'PathNodeStudy',
    resource: 'ResourceGenerator',
    visualizer: 'AlgorithmVisualizer',
  }
  return map[module] ?? module
}

// 个人中心旧看板兼容：后端旧 time-stats 路由已移除，改由最新评估事实快照转换。
function toRangeDays(days: number): 7 | 14 | 30 | undefined {
  return days === 7 || days === 14 || days === 30 ? days : undefined
}

function localDateKey(date = new Date()): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export async function getLearningTimeStats(days = 7) {
  const facts = await getLatestFacts(toRangeDays(days))
  const dailyBreakdown = facts?.activity.daily_minutes.map(item => ({
    date: item.date,
    seconds: item.minutes * 60,
  })) ?? []
  const todayKey = localDateKey()
  const todaySeconds = dailyBreakdown.find(item => item.date === todayKey)?.seconds ?? 0
  const contextBreakdown = (facts?.activity.module_distribution ?? []).reduce<Record<string, number>>((acc, item) => {
    acc[moduleToProfileContext(item.module)] = item.count
    return acc
  }, {})

  return {
    data: {
      code: 200,
      message: 'success',
      data: {
        total_seconds: (facts?.activity.total_minutes ?? 0) * 60,
        today_seconds: todaySeconds,
        streak_days: facts?.activity.active_days ?? 0,
        daily_breakdown: dailyBreakdown,
        context_breakdown: contextBreakdown,
      },
    },
  }
}

// 个人中心旧看板兼容：旧 summary 路由不恢复，只把最新评估事实与当前策略转为旧 UI 需要的摘要。
export async function getEvaluationSummary(_limit = 100) {
  const [facts, strategyResponse] = await Promise.all([
    getLatestFacts(),
    http.get<ApiResponse<GuidanceStrategyResponse>>('/ai/evaluation/guidance-strategy').catch(() => null),
  ])
  const strategy = strategyResponse?.data.data.guidance_strategy ?? null
  const moduleCount = facts?.activity.module_distribution.reduce((sum, item) => sum + item.count, 0) ?? 0

  return {
    data: {
      code: 200,
      message: 'success',
      data: {
        completed_resources: facts?.resource_usage.completed ?? 0,
        viewed_resources: facts?.resource_usage.viewed ?? 0,
        event_count: moduleCount,
        weak_topics: facts?.data_quality.insufficient_topics ?? [],
        focus_topics: strategy?.focus_topics ?? [],
        recommendations: [
          strategy?.conclusion,
          strategy?.reason,
        ].filter((item): item is string => Boolean(item)),
      },
    },
  }
}
