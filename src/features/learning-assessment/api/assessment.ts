import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  LearningAssessmentReport,
  ReportsHistoryResponse,
  GuidanceStrategyResponse,
} from '@/features/learning-assessment/model/assessment'

export type {
  LearningAssessmentReport,
  ReportsHistoryResponse,
  GuidanceStrategyResponse,
}

export function generateAssessmentReport(rangeDays: 3 | 7 | 14) {
  return http.post<ApiResponse<LearningAssessmentReport>>('/ai/evaluation/reports', { range_days: rangeDays })
}

export function getLatestReport() {
  return http.get<ApiResponse<LearningAssessmentReport | null>>('/ai/evaluation/reports/latest')
}

export function getReportsHistory(page = 1, pageSize = 10) {
  return http.get<ApiResponse<ReportsHistoryResponse>>('/ai/evaluation/reports', {
    params: { page, page_size: pageSize },
  })
}

export function getReportDetail(reportId: number) {
  return http.get<ApiResponse<LearningAssessmentReport>>(`/ai/evaluation/reports/${reportId}`)
}

export function getGuidanceStrategy() {
  return http.get<ApiResponse<GuidanceStrategyResponse>>('/ai/evaluation/guidance-strategy')
}
