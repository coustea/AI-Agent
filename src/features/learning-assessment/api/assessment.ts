import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  LearningAssessment,
  AssessmentsHistoryResponse,
  GuidanceStrategyResponse,
} from '@/features/learning-assessment/model/assessment'
import type { DashboardData } from '@/features/evaluation/api/evaluation'

export type {
  LearningAssessment,
  AssessmentsHistoryResponse,
  GuidanceStrategyResponse,
}

export function generateAssessment(rangeDays: 3 | 7 | 14) {
  return http.post<ApiResponse<LearningAssessment>>('/ai/evaluation/assessments', { range_days: rangeDays })
}

export function getLatestAssessment() {
  return http.get<ApiResponse<LearningAssessment | null>>('/ai/evaluation/assessments/latest')
}

export function getAssessmentsHistory(page = 1, pageSize = 10) {
  return http.get<ApiResponse<AssessmentsHistoryResponse>>('/ai/evaluation/assessments', {
    params: { page, page_size: pageSize },
  })
}

export function getAssessmentDetail(assessmentId: number) {
  return http.get<ApiResponse<LearningAssessment>>(`/ai/evaluation/assessments/${assessmentId}`)
}

export function getGuidanceStrategy() {
  return http.get<ApiResponse<GuidanceStrategyResponse>>('/ai/evaluation/guidance-strategy')
}

export function getAssessmentDashboard(assessmentId: number) {
  return http.get<ApiResponse<DashboardData>>(`/ai/evaluation/assessments/${assessmentId}/dashboard`)
}
