import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  AlgorithmInfo,
  RunResult,
  TemplateData,
} from '@/features/algorithm-visualization/types'

// 获取受信、可视化的算法模板目录。
export function fetchAlgorithms() {
  return http.get<ApiResponse<AlgorithmInfo[]>>('/ai/algorithm-visualizer/templates')
}

// 获取一个模板的真实源码和输入契约。
export function fetchTemplate(templateKey: string) {
  return http.get<ApiResponse<TemplateData>>(`/ai/algorithm-visualizer/templates/${templateKey}`)
}

// 运行注册模板。客户端只能提交该模板声明的输入。
export function runVisualization(templateKey: string, data: {
  inputData?: Record<string, unknown>
}) {
  return http.post<ApiResponse<RunResult>>(`/ai/algorithm-visualizer/templates/${templateKey}/runs`, data)
}
