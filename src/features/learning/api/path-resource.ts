import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  PathGeneratedResourceItem,
} from '@/features/resource/api/resource-history'
import type { PathResourceDetail } from '@/features/learning/model/path'

export function getPathGeneratedResources(page = 1, limit = 20) {
  const offset = (page - 1) * limit
  return http.get<ApiResponse<{ items: PathGeneratedResourceItem[], total: number }>>('/ai/path-plan/resources', {
    params: { limit, offset }
  })
}

export function getPathGeneratedResourceDetail(resourceId: number) {
  return http.get<ApiResponse<PathResourceDetail>>(`/ai/path-plan/resources/${resourceId}`)
}
