import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'

// ==========================================
// 类型定义
// ==========================================

export interface SchoolItem {
  id: number
  name: string
  level: string | null
}

// ==========================================
// 学校搜索 API
// ==========================================

export function searchSchools(keyword: string = '', limit = 20) {
  return http.get<ApiResponse<SchoolItem[]>>('/ai/schools/search', {
    params: { keyword, limit }
  })
}