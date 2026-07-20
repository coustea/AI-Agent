import { ref } from 'vue'
import { getErrorMessage } from '@/shared/api/http'
import { runVisualization } from '@/features/algorithm-visualization/api/algorithmVisualizer'
import type {
  RunError,
  RunResult,
  TraceEvent,
} from '@/features/algorithm-visualization/types'

// 提交运行→获取 TraceEvent[]
export function useAlgorithmRun() {
  // 可视化事件列表、运行结果、错误信息、加载状态
  const events = ref<TraceEvent[]>([])
  const runResult = ref<RunResult | null>(null)
  const runError = ref<RunError | null>(null)
  const generating = ref(false)
  const runVersion = ref(0)

  // 运行注册模板，获取可视化追踪事件
  async function run(params: {
    algorithm: string
    inputData?: Record<string, unknown>
  }) {
    generating.value = true
    runError.value = null
    runResult.value = null
    events.value = []
    try {
      const resp = await runVisualization(params.algorithm, { inputData: params.inputData })
      runResult.value = resp.data.data
      events.value = runResult.value?.events ?? []
      if (events.value.length === 0) {
        runError.value = {
          errorType: 'TRACE_EVENT_EMPTY',
          message: '代码运行完毕，但未产生任何可视化追踪记录。',
        }
      } else {
        runVersion.value += 1
      }
    } catch (err: unknown) {
      const msg = getErrorMessage(err, '运行失败，请检查代码或 Python 运行时。')
      // Extract errorType from backend response data if available
      const responseData = (err as { response?: { data?: { data?: { errorType?: string } } } })?.response?.data?.data
      runError.value = {
        errorType: (responseData?.errorType as RunError['errorType']) || 'RUNTIME_ERROR',
        message: msg,
        details: (err as { details?: string })?.details,
      }
    } finally {
      generating.value = false
    }
  }

  // 清空运行结果与事件
  function clear() {
    events.value = []
    runResult.value = null
    runError.value = null
  }

  return { events, runResult, runError, generating, runVersion, run, clear }
}
