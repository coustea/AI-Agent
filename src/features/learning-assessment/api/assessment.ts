import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  LearningAssessment,
  AssessmentsHistoryResponse,
} from '@/features/learning-assessment/model/assessment'
import type { DashboardData } from '@/features/evaluation/api/evaluation'

export type {
  LearningAssessment,
  AssessmentsHistoryResponse,
}

export function generateAssessment() {
  // LLM 生成评估需要较长时间，设置 60 秒超时
  // range_days 由后端默认为 7 天，前端不再提供选择
  return http.post<ApiResponse<LearningAssessment>>('/ai/evaluation/assessments', { range_days: 7 }, { timeout: 60000 })
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

export function getAssessmentDashboard(assessmentId: number) {
  return http.get<ApiResponse<DashboardData>>(`/ai/evaluation/assessments/${assessmentId}/dashboard`)
}
