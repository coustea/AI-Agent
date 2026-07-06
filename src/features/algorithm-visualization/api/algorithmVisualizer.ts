import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  AlgorithmInfo,
  CodeLanguage,
  LanguageInfo,
  RunResult,
  TemplateData,
  TraceDomain,
} from '@/features/algorithm-visualization/types'

/** 获取支持语言列表 — useAlgorithmTemplate 调用 */
export function fetchLanguages() {
  return http.get<ApiResponse<LanguageInfo[]>>('/ai/algorithm-visualizer/languages')
}

/** 获取算法列表 — useAlgorithmTemplate 调用 */
export function fetchAlgorithms(domain: TraceDomain = 'data_structure') {
  return http.get<ApiResponse<AlgorithmInfo[]>>('/ai/algorithm-visualizer/algorithms', {
    params: { domain },
  })
}

/** 获取代码模板 — useAlgorithmTemplate 调用 */
export function fetchTemplate(algorithm: string, language: CodeLanguage) {
  return http.get<ApiResponse<TemplateData>>('/ai/algorithm-visualizer/templates', {
    params: { algorithm, language },
  })
}

/** 运行可视化 — useAlgorithmRun 调用 */
export function runVisualization(data: {
  domain: TraceDomain
  algorithm: string
  visualizerType: string
  language: CodeLanguage
  code: string
}) {
  return http.post<ApiResponse<RunResult>>('/ai/algorithm-visualizer/run', data)
}
