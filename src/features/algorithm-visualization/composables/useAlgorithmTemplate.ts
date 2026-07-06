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

/** 算法+语言→模板代码加载。AlgorithmVisualization.vue 使用。
 * 替代旧 useVisualizerState.ts。 */
export function useAlgorithmTemplate() {
  const language = ref<CodeLanguage>('python')
  const algorithm = ref<string>('bubble_sort')
  const code = ref('')
  const templateData = ref<TemplateData | null>(null)
  const loading = ref(false)

  const languages = ref<LanguageInfo[]>([])
  const algorithms = ref<AlgorithmInfo[]>([])
  const metaLoading = ref(false)

  async function loadMeta() {
    metaLoading.value = true
    try {
      const [langsRes, algsRes] = await Promise.all([fetchLanguages(), fetchAlgorithms()])
      languages.value = langsRes.data.data ?? []
      algorithms.value = algsRes.data.data ?? []
    } catch {
      toast.error('加载语言或算法列表失败')
    } finally {
      metaLoading.value = false
    }
  }

  async function loadTemplate() {
    loading.value = true
    try {
      const resp = await fetchTemplate(algorithm.value, language.value)
      templateData.value = resp.data.data
      code.value = templateData.value?.templateCode ?? ''
    } catch {
      toast.error('加载模板失败')
    } finally {
      loading.value = false
    }
  }

  /** 切换语言/算法时自动重载模板 */
  watch([language, algorithm], () => {
    loadTemplate()
  })

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
