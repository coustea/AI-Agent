import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  AlgorithmInfo,
  CodeLanguage,
  LanguageInfo,
  RunResult,
  TemplateData,
  VisualizerType,
} from '@/features/algorithm-visualization/types'

// 获取支持语言列表
export function fetchLanguages() {
  return http.get<ApiResponse<LanguageInfo[]>>('/ai/algorithm-visualizer/languages')
}

// 获取算法列表，domain 默认 all；language 可选
export function fetchAlgorithms(domain = 'all', language?: CodeLanguage) {
  return http.get<ApiResponse<AlgorithmInfo[]>>('/ai/algorithm-visualizer/algorithms', {
    params: { domain, ...(language ? { language } : {}) },
  })
}

// 获取代码模板
export function fetchTemplate(algorithm: string, language: CodeLanguage) {
  return http.get<ApiResponse<TemplateData>>('/ai/algorithm-visualizer/templates', {
    params: { algorithm, language },
  })
}

// 运行可视化，超时 60s（后端需 LLM 插装 + 沙箱执行）
export function runVisualization(data: {
  domain: string
  algorithm: string
  visualizerType: VisualizerType
  language: CodeLanguage
  code: string
  inputData?: Record<string, unknown>
}) {
  return http.post<ApiResponse<RunResult>>('/ai/algorithm-visualizer/run', data, {
    timeout: 60000,
  })
}
