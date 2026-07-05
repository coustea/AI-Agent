import { getErrorMessage } from '@/shared/api/http'
import { generateAlgorithmVisualization } from '@/features/algorithm-visualization/api/algorithmVisualizer'
import { createBubbleSortPayload } from '@/features/algorithm-visualization/mock/algorithmVisualizerMock'
import type {
  VisualizerGenerationParams,
  VisualizerPayload,
} from '@/features/algorithm-visualization/types'

export interface VisualizerPayloadResult {
  payload: VisualizerPayload
  source: 'api' | 'mock'
  message: string
}

export async function resolveVisualizerPayload(
  params: VisualizerGenerationParams,
): Promise<VisualizerPayloadResult> {
  try {
    const response = await generateAlgorithmVisualization(params)
    return {
      payload: response.data.data,
      source: 'api',
      message: '已使用接口返回的可视化步骤。',
    }
  } catch (error) {
    return {
      payload: createBubbleSortPayload(params),
      source: 'mock',
      message: `${getErrorMessage(error, '可视化接口暂不可用')}，已回退到前端冒泡排序 mock。`,
    }
  }
}
