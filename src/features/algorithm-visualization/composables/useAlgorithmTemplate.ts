import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'
import { fetchAlgorithms, fetchLanguages, fetchTemplate } from '@/features/algorithm-visualization/api/algorithmVisualizer'
import type {
  AlgorithmInfo,
  CodeLanguage,
  LanguageInfo,
  TemplateData,
  VisualizerType,
} from '@/features/algorithm-visualization/types'

// 算法+语言→模板代码加载
export function useAlgorithmTemplate() {
  // 当前选中的语言、算法 key、编辑器代码、模板数据、加载中状态
  const language = ref<CodeLanguage>('python')
  const algorithm = ref<string>('bubble_sort')
  const code = ref('')
  const templateData = ref<TemplateData | null>(null)
  const loading = ref(false)
  const templateVersion = ref(0)

  // 语言列表、算法列表、元数据加载状态、当前算法对象（根据 algorithm key 计算）
  const languages = ref<LanguageInfo[]>([])
  const algorithms = ref<AlgorithmInfo[]>([])
  const metaLoading = ref(false)
  const currentAlgorithm = computed(() => {
    return algorithms.value.find((item) => item.key === algorithm.value) ?? null
  })

  let _loadSeq = 0

  // 当算法或语言变更时，确保当前选择在有效范围内
  function normalizeSelection() {
    let changed = false

    if (!currentAlgorithm.value && algorithms.value.length > 0) {
      algorithm.value = algorithms.value[0]!.key
      changed = true
    }

    const selected = currentAlgorithm.value
    if (selected?.supportedLanguages.length && !selected.supportedLanguages.includes(language.value)) {
      language.value = selected.supportedLanguages[0]!
      changed = true
    }

    return changed
  }

  // 初始加载语言列表和算法列表
  async function loadMeta() {
    metaLoading.value = true
    try {
      const [langsRes, algsRes] = await Promise.all([
        fetchLanguages(),
        fetchAlgorithms('all'),
      ])
      languages.value = langsRes.data.data ?? []
      algorithms.value = algsRes.data.data ?? []
      normalizeSelection()
    } catch {
      toast.error('加载语言或算法列表失败')
    } finally {
      metaLoading.value = false
    }
  }

  // 根据当前选中的算法和语言加载代码模板
  async function loadTemplate() {
    if (!algorithm.value || !language.value) return

    const mySeq = ++_loadSeq
    loading.value = true
    try {
      const resp = await fetchTemplate(algorithm.value, language.value)
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

    if (selected.supportedLanguages.length && !selected.supportedLanguages.includes(language.value)) {
      language.value = selected.supportedLanguages[0]!
    }

    await loadTemplate()
    return true
  }

  // 语言切换也必须同步刷新当前模板源码。
  async function setLanguage(nextLanguage: CodeLanguage) {
    if (language.value === nextLanguage) return
    language.value = nextLanguage
    await loadTemplate()
  }

  // 重置模板为当前算法+语言的初始代码
  function resetTemplate() {
    return loadTemplate()
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
    language,
    algorithm,
    code,
    templateData,
    templateVersion,
    loading,
    languages,
    algorithms,
    metaLoading,
    currentAlgorithm,
    loadMeta,
    loadTemplate,
    resetTemplate,
    setAlgorithm,
    setLanguage,
    normalizeSelection,
    getCurrentAlgorithmInfo,
    getCurrentVisualizerType,
  }
}
