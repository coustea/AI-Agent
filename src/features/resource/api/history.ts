import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'

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
  metrics: Record<string, unknown>
  downstream_context?: Record<string, unknown> | null
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
