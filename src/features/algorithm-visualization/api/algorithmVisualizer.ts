import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  AlgorithmInfo,
  CodeLanguage,
  CustomCodeContract,
  LanguageInfo,
  RunResult,
  TemplateData,
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

// 解析用户函数签名，生成无需 JSON 的运行参数表单；不调用 LLM。
export function fetchCustomCodeContract(code: string, entryFunction?: string) {
  return http.post<ApiResponse<CustomCodeContract>>('/ai/algorithm-visualizer/custom-contract', {
    code,
    ...(entryFunction ? { entryFunction } : {}),
  })
}

// 运行注册的官方模板；源码只用于展示和步骤定位，不参与请求执行。
export function runVisualization(data: {
  mode: 'official' | 'custom'
  algorithm?: string
  language: CodeLanguage
  inputData?: Record<string, unknown>
  code?: string
  visualizerType?: string
  entryFunction?: string
}) {
  return http.post<ApiResponse<RunResult>>('/ai/algorithm-visualizer/run', data, {
    timeout: 15000,
  })
}
