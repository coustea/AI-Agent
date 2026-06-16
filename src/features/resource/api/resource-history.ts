import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type { PathResourceDetail } from '@/features/learning/model/path'

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
  content: Record<string, unknown> | string | null
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

export function getGeneratedResources(page = 1, limit = 20) {
  const offset = (page - 1) * limit
  return http.get<ApiResponse<{ items: GeneratedResourceItem[], total: number }>>('/ai/resources', {
    params: { limit, offset }
  })
}

export function getGeneratedResourceDetail(resourceId: number) {
  return http.get<ApiResponse<GeneratedResourceBundle>>(`/ai/resources/${resourceId}`)
}

export interface PathGeneratedResourceItem extends GeneratedResourceItem {
  path_id: number | null
  node_id: string | null
  path_node_id: number | null
  node_title: string | null
  resource_type?: string | null
  title?: string | null
  summary?: string | null
  error_message?: string | null
}

export type { PathResourceDetail }
