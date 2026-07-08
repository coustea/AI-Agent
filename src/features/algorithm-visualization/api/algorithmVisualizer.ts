import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  AlgorithmInfo,
  CodeLanguage,
  LanguageInfo,
  RunResult,
  TemplateData,
} from '@/features/algorithm-visualization/types'

/** 获取支持语言列表 — useAlgorithmTemplate 调用 */
export function fetchLanguages() {
  return http.get<ApiResponse<LanguageInfo[]>>('/ai/algorithm-visualizer/languages')
}

/** 获取算法列表 — useAlgorithmTemplate 调用。
 *  domain 默认 all；language 可选，传入后只返回支持该语言的算法。 */
export function fetchAlgorithms(domain = 'all', language?: CodeLanguage) {
  return http.get<ApiResponse<AlgorithmInfo[]>>('/ai/algorithm-visualizer/algorithms', {
    params: { domain, ...(language ? { language } : {}) },
  })
}

/** 获取代码模板 — useAlgorithmTemplate 调用 */
export function fetchTemplate(algorithm: string, language: CodeLanguage) {
  return http.get<ApiResponse<TemplateData>>('/ai/algorithm-visualizer/templates', {
    params: { algorithm, language },
  })
}

/** 运行可视化 — useAlgorithmRun 调用。
 *  超时 60s：后端可能需要 LLM 自动插装 + 沙箱执行。 */
export function runVisualization(data: {
  algorithm: string
  visualizerType: string
  language: CodeLanguage
  code: string
  inputData?: string
}) {
  return http.post<ApiResponse<RunResult>>('/ai/algorithm-visualizer/run', data, {
    timeout: 60000,
  })
}
