import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  VisualizerGenerationParams,
  VisualizerPayload,
} from '@/features/algorithm-visualization/types'

export function generateAlgorithmVisualization(data: VisualizerGenerationParams) {
  return http.post<ApiResponse<VisualizerPayload>>('/ai/algorithm-visualizer/generate', data)
}
