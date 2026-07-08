// 封装带 JWT 拦截的 axios 实例与统一响应信封类型
import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'

// ==========================================
// 类型定义
// ==========================================

// 资源生成历史列表中的单条记录摘要
export interface GeneratedResourceItem {
  id: number // 资源生成任务主键
  learning_need: string | null // 用户输入的学习需求文本
  status: string // 任务状态：pending / generating / completed / failed 等
  resource_types: string[] // 本次任务产出的资源类型列表（content / mindmap / quiz …）
  created_at: string | null // 任务创建时间（ISO 字符串）
  updated_at: string | null // 任务最近更新时间（ISO 字符串）
}

// 单个资源产物的详细信息：对应后端 generated_resource_items 表的一行
export interface ResourceItemDetail {
  id: number // 产物记录主键
  type: string // 产物类型：content / mindmap / quiz / code / reading / ppt / cartoon / video
  title: string // 产物标题
  format: string // 产物格式：markdown / json / html / pptx / mp4 等
  content: Record<string, unknown> | string | null // 产物正文内容，结构因类型而异
  summary: string // 产物摘要
  metrics: Record<string, unknown> // 生成过程指标（耗时、token 数等）
  downstream_context?: Record<string, unknown> | null // 传递给下游智能体的上下文片段
  metadata: Record<string, unknown> // 额外元数据（模板、版本号等）
  status: string // 单产物状态：completed / failed / generating
  error_message: string | null // 失败时的错误信息，成功时为 null
  created_at: string | null // 产物创建时间
  updated_at: string | null // 产物最近更新时间
}

// 一次资源生成任务的完整产物包：包含任务元信息与全部产物明细
export interface GeneratedResourceBundle {
  id: string // 任务唯一标识（前端字符串化后的 resource_id）
  task_id: string // 后端任务追踪 ID
  title: string // 任务标题
  learning_need: string // 用户输入的学习需求
  selected_agents: string[] // 参与生成的智能体 id 列表
  resources: ResourceItemDetail[] // 全部产物明细列表
  status: string // 任务整体状态
  created_at: string | null // 任务创建时间
  updated_at: string | null // 任务最近更新时间
  metadata: Record<string, unknown> // 任务级元数据（场景、配置快照等）
}

// ==========================================
// 资源生成历史 API
// ==========================================

// 分页获取资源生成历史列表 GET /api/v1/ai/resources?limit=&offset=
export function getGeneratedResources(page = 1, limit = 20) {
  // 将页码转换为偏移量供后端分页查询
  const offset = (page - 1) * limit
  return http.get<ApiResponse<{ items: GeneratedResourceItem[], total: number }>>('/ai/resources', {
    params: { limit, offset }
  })
}

// 获取单个资源生成任务的完整详情（含全部产物） GET /api/v1/ai/resources/:resourceId
export function getGeneratedResourceDetail(resourceId: number) {
  return http.get<ApiResponse<GeneratedResourceBundle>>(`/ai/resources/${resourceId}`)
}
