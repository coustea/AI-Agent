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

// 单个资源产物的详细信息：与后端 GeneratedResourceItem 完全对齐
export interface ResourceItemDetail {
  id: string // 产物记录主键（UUID）
  type: string // 产物类型：content / mindmap / quiz / code / reading / ppt / cartoon
  title: string // 产物标题
  format: string // 产物格式：markdown / json / html / pptx / mp4 等
  content: Record<string, unknown> | string | null // 产物正文内容，结构因类型而异
  metadata: Record<string, unknown> // 额外元数据（模板、版本号等）
  created_at: string | null // 产物创建时间
}

// 一次资源生成任务的完整产物包：与后端 ResourceBundle 完全对齐
export interface GeneratedResourceBundle {
  id: string // 任务唯一标识（前端字符串化后的 resource_id）
  title: string // 任务标题
  learning_need: string // 用户输入的学习需求
  selected_agents: string[] // 参与生成的智能体 id 列表
  plan_content: string | null // 教学计划 Markdown 内容
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
