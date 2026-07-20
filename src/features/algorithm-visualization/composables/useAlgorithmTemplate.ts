import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'
import { fetchAlgorithms, fetchTemplate } from '@/features/algorithm-visualization/api/algorithmVisualizer'
import type {
  AlgorithmInfo,
  TemplateData,
  VisualizerType,
} from '@/features/algorithm-visualization/types'

// 已注册模板目录与源码加载。
export function useAlgorithmTemplate() {
  // 当前算法 key、后端模板源码、模板数据和加载状态。
  const algorithm = ref<string>('bubble_sort')
  const code = ref('')
  const templateData = ref<TemplateData | null>(null)
  const loading = ref(false)
  const templateVersion = ref(0)

  // 算法目录、加载状态、当前算法对象（根据 algorithm key 计算）
  const algorithms = ref<AlgorithmInfo[]>([])
  const metaLoading = ref(false)
  const currentAlgorithm = computed(() => {
    return algorithms.value.find((item) => item.key === algorithm.value) ?? null
  })

  let _loadSeq = 0

  // 当模板目录变化时，确保当前选择仍然有效。
  function normalizeSelection() {
    let changed = false

    if (!currentAlgorithm.value && algorithms.value.length > 0) {
      algorithm.value = algorithms.value[0]!.key
      changed = true
    }

    return changed
  }

  // 初始加载模板目录。
  async function loadMeta() {
    metaLoading.value = true
    try {
      const response = await fetchAlgorithms()
      algorithms.value = response.data.data ?? []
      normalizeSelection()
    } catch {
      toast.error('加载算法模板列表失败')
    } finally {
      metaLoading.value = false
    }
  }

  // 根据当前算法加载其实际执行源码。
  async function loadTemplate() {
    if (!algorithm.value) return

    const mySeq = ++_loadSeq
    loading.value = true
    try {
      const resp = await fetchTemplate(algorithm.value)
      if (mySeq !== _loadSeq) return
      templateData.value = resp.data.data
      code.value = templateData.value?.templateCode ?? ''
      templateVersion.value += 1
    } catch {
      if (mySeq !== _loadSeq) return
      toast.error('加载模板失败')
    } finally {
      if (mySeq === _loadSeq) {
        loading.value = false
      }
    }
  }

  // 设置当前算法并加载模板。选择和源码同步必须处于同一显式流程，
  // 不能依赖 watch 的异步调度，否则编辑器可能显示上一次模板的源码。
  async function setAlgorithm(nextAlgorithm: string) {
    const selected = algorithms.value.find((item) => item.key === nextAlgorithm)
    if (!selected) return false

    algorithm.value = selected.key

    await loadTemplate()
    return true
  }

  // 获取当前算法信息
  function getCurrentAlgorithmInfo(): AlgorithmInfo | undefined {
    return currentAlgorithm.value ?? undefined
  }

  // 获取当前可视化器类型
  function getCurrentVisualizerType(): VisualizerType {
    return getCurrentAlgorithmInfo()?.visualizerType ?? 'array'
  }

  return {
    algorithm,
    code,
    templateData,
    templateVersion,
    loading,
    algorithms,
    metaLoading,
    currentAlgorithm,
    loadMeta,
    loadTemplate,
    setAlgorithm,
    normalizeSelection,
    getCurrentAlgorithmInfo,
    getCurrentVisualizerType,
  }
}
