import { computed, type Ref } from 'vue'
import type { TraceEvent, VisualizerType } from '@/features/algorithm-visualization/types'

/** 从 TraceEvent 列表中提取 visualizerType。
 * AlgorithmVisualization.vue + VisualizerCanvas.vue 使用。 */
export function useVisualizerResolver(events: Ref<TraceEvent[]>) {
  const visualizerType = computed<VisualizerType>(() => {
    const first = events.value[0]
    return first?.visualizerType ?? 'array'
  })

  return { visualizerType }
}
