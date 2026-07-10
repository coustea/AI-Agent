import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type { SchoolItem } from '../model/school'

// 根据关键词搜索学校列表（用于输入联想）
export function searchSchools(keyword: string = '', limit = 20) {
  return http.get<ApiResponse<SchoolItem[]>>('/ai/schools/search', {
    params: { keyword, limit }
  })
}
