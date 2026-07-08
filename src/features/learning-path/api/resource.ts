import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type { PathResourceDetail } from '@/features/learning-path/model/path'

export interface PathGeneratedResourceItem {
  id: number
  path_id: number | null
  path_node_id: number | null
  node_id: number | null
  node_title: string
  title: string | null
  learning_need: string | null
  resource_type: string | null
  resource_types: string[]
  status: string
  error_message: string | null
  summary: string | null
  created_at: string | null
  updated_at: string | null
}

export function getPathGeneratedResources(page = 1, limit = 20) {
  const offset = (page - 1) * limit
  return http.get<ApiResponse<{ items: PathGeneratedResourceItem[], total: number }>>('/ai/path-plan/resources', {
    params: { limit, offset }
  })
}

export function getPathGeneratedResourceDetail(resourceId: number) {
  return http.get<ApiResponse<PathResourceDetail>>(`/ai/path-plan/resources/${resourceId}`)
}
