import { ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { fetchAlgorithms, fetchLanguages, fetchTemplate } from '@/features/algorithm-visualization/api/algorithmVisualizer'
import type {
  AlgorithmInfo,
  CodeLanguage,
  LanguageInfo,
  TemplateData,
  VisualizerType,
} from '@/features/algorithm-visualization/types'

/** 算法+语言→模板代码加载。AlgorithmVisualization.vue 使用。 */
export function useAlgorithmTemplate() {
  const language = ref<CodeLanguage>('python')
  const algorithm = ref<string>('bubble_sort')
  const code = ref('')
  const templateData = ref<TemplateData | null>(null)
  const loading = ref(false)

  const languages = ref<LanguageInfo[]>([])
  const algorithms = ref<AlgorithmInfo[]>([])
  const metaLoading = ref(false)

  /** 去重：同一 (algorithm, language) 的并发 loadTemplate 只执行一次 */
  let _loadSeq = 0

  async function loadMeta() {
    metaLoading.value = true
    try {
      const [langsRes, algsRes] = await Promise.all([
        fetchLanguages(),
        fetchAlgorithms('all', language.value),
      ])
      languages.value = langsRes.data.data ?? []
      algorithms.value = algsRes.data.data ?? []
    } catch {
      toast.error('加载语言或算法列表失败')
    } finally {
      metaLoading.value = false
    }
  }

  /** 切换语言时重新加载算法列表（只显示支持当前语言的算法） */
  async function reloadAlgorithms() {
    try {
      const algsRes = await fetchAlgorithms('all', language.value)
      algorithms.value = algsRes.data.data ?? []

      // 如果当前算法不在新列表里，自动切换到第一个可用算法
      const stillAvailable = algorithms.value.some((a) => a.key === algorithm.value)
      if (!stillAvailable && algorithms.value.length > 0) {
        algorithm.value = algorithms.value[0]!.key
      }
    } catch {
      toast.error('加载算法列表失败')
    }
  }

  async function loadTemplate() {
    // 递增序号，后续并发调用会因序号不匹配而跳过
    const mySeq = ++_loadSeq
    loading.value = true
    try {
      const resp = await fetchTemplate(algorithm.value, language.value)
      // 只有最新一次调用的结果才写入，避免竞态覆盖
      if (mySeq !== _loadSeq) return
      templateData.value = resp.data.data
      code.value = templateData.value?.templateCode ?? ''
    } catch {
      if (mySeq !== _loadSeq) return
      toast.error('加载模板失败')
    } finally {
      if (mySeq === _loadSeq) {
        loading.value = false
      }
    }
  }

  /** 切换算法时自动重载模板 */
  watch(
    [algorithm],
    () => {
      loadTemplate()
    },
    { immediate: false },
  )

  /** 切换语言时先更新算法列表，再加载模板 */
  watch(
    [language],
    async () => {
      await reloadAlgorithms()
      // reloadAlgorithms 可能会更改 algorithm，后续的 algorithm watch 会触发 loadTemplate
      // 但如果 algorithm 没变，也需要重新加载模板（因为语言变了）
      loadTemplate()
    },
  )

  /** 重置到默认模板 */
  function resetTemplate() {
    loadTemplate()
  }

  /** 根据算法 key 获取当前算法信息 */
  function getCurrentAlgorithmInfo(): AlgorithmInfo | undefined {
    return algorithms.value.find((a) => a.key === algorithm.value)
  }

  /** 获取当前算法的 visualizerType */
  function getCurrentVisualizerType(): VisualizerType {
    return getCurrentAlgorithmInfo()?.visualizerType ?? 'array'
  }

  return {
    language,
    algorithm,
    code,
    templateData,
    loading,
    languages,
    algorithms,
    metaLoading,
    loadMeta,
    loadTemplate,
    resetTemplate,
    getCurrentAlgorithmInfo,
    getCurrentVisualizerType,
  }
}
