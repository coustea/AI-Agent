import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { getErrorMessage } from '@/shared/api/http'
import { runVisualization } from '@/features/algorithm-visualization/api/algorithmVisualizer'
import type {
  CodeLanguage,
  RunError,
  RunResult,
  TraceEvent,
  VisualizerType,
} from '@/features/algorithm-visualization/types'

/** 提交运行→获取 TraceEvent[]。AlgorithmVisualization.vue 使用。 */
export function useAlgorithmRun() {
  const events = ref<TraceEvent[]>([])
  const runResult = ref<RunResult | null>(null)
  const runError = ref<RunError | null>(null)
  const generating = ref(false)

  async function run(params: {
    algorithm: string
    visualizerType: VisualizerType
    language: CodeLanguage
    code: string
    inputData?: string
  }) {
    generating.value = true
    runError.value = null
    events.value = []
    try {
      const resp = await runVisualization(params)
      runResult.value = resp.data.data
      events.value = runResult.value?.events ?? []
      if (events.value.length > 0) {
        toast.success('算法运行成功，可视化步骤已载入！')
      } else {
        runError.value = {
          errorType: 'TRACE_EVENT_EMPTY',
          message: '代码运行完毕，但未产生任何可视化追踪记录。',
        }
        toast.warning('运行完成但未产生可视化事件')
      }
    } catch (err: unknown) {
      const msg = getErrorMessage(err, '运行失败，请检查后端服务状态。')
      runError.value = {
        errorType: 'RUNTIME_ERROR',
        message: msg,
      }
      toast.error(msg)
    } finally {
      generating.value = false
    }
  }

  function clear() {
    events.value = []
    runResult.value = null
    runError.value = null
  }

  return { events, runResult, runError, generating, run, clear }
}
