// 封装带 JWT 拦截的 axios 实例与统一响应信封类型
import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
// 引入资源生成请求体类型与任务状态类型，保持前后端字段对齐
import type {
  ResourceGenerationRequest,
  ResourceTaskStatus,
} from '@/features/resource/model/resource'

// PPT 模板选项：供用户在前端选择幻灯片模板时使用
export interface PptTemplateOption {
  id: string // 模板唯一标识
  name: string // 模板展示名称
  description: string // 模板描述文案
  family: string // 模板所属系列（如 instructional / technical）
  scheme: string // 模板配色方案标识
  tags: string[] // 模板标签列表，用于筛选与分类
}

// ==========================================
// 资源生成 API
// ==========================================

// 发起资源生成任务 POST /ai/resources，请求体为 ResourceGenerationRequest
export function startResourceGeneration(params: ResourceGenerationRequest) {
  return http.post<ApiResponse<{ resource_id: number; status: string }>>('/ai/resources', params)
}

// 轮询资源生成任务状态 GET /ai/resources/:resourceId/status
export function pollResourceStatus(resourceId: number) {
  return http.get<ApiResponse<ResourceTaskStatus>>(`/ai/resources/${resourceId}/status`)
}

// 获取资源生成任务的完整产物包 GET /ai/resources/:resourceId（超时 30s 以应对大产物）
export function getResourceBundle(resourceId: number) {
  return http.get<ApiResponse<any>>(`/ai/resources/${resourceId}`, { timeout: 30000 })
}

// 获取可选 PPT 模板列表 GET /ai/resources/ppt/templates
export function getPptTemplates() {
  return http.get<ApiResponse<PptTemplateOption[]>>('/ai/resources/ppt/templates')
}
