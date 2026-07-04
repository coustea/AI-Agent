import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type { SchoolItem } from '../model/school'

export function searchSchools(keyword: string = '', limit = 20) {
  return http.get<ApiResponse<SchoolItem[]>>('/ai/schools/search', {
    params: { keyword, limit }
  })
}
