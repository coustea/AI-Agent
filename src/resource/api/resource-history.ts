import http from '@/shared/utils/http'
import type { ApiResponse } from '@/shared/utils/http'

// ==========================================
// 类型定义
// ==========================================

export interface GeneratedResourceItem {
  id: number
  learning_need: string | null
  status: string
  resource_types: string[]
  created_at: string | null
  updated_at: string | null
}

export interface ResourceItemDetail {
  id: number
  type: string
  title: string
  format: string
  content: string | null
  summary: string
  summary_data: Record<string, unknown>
  metadata: Record<string, unknown>
  status: string
  error_message: string | null
  created_at: string | null
  updated_at: string | null
}

export interface GeneratedResourceBundle {
  id: string
  task_id: string
  title: string
  learning_need: string
  selected_agents: string[]
  resources: ResourceItemDetail[]
  study_path: unknown[]
  review_result: unknown
  status: string
  created_at: string | null
  updated_at: string | null
  metadata: Record<string, unknown>
}

// ==========================================
// 资源生成历史 API
// ==========================================

export function getGeneratedResources(limit = 20) {
  return http.get<ApiResponse<GeneratedResourceItem[]>>('/ai/resources', {
    params: { limit }
  })
}

export function getGeneratedResourceDetail(resourceId: number) {
  return http.get<ApiResponse<GeneratedResourceBundle>>(`/ai/resources/${resourceId}`)
}