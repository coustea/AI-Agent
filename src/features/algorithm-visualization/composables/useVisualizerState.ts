import { ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { resolveVisualizerPayload } from '@/features/algorithm-visualization/composables/useVisualizerPayload'
import { createBubbleSortPayload } from '@/features/algorithm-visualization/mock/algorithmVisualizerMock'
import {
  DEFAULT_VISUALIZER_INPUT,
  DEFAULT_VISUALIZER_LANGUAGE,
  getDefaultVisualizerCode,
} from '@/features/algorithm-visualization/presets/visualizerPresets'
import type {
  CodeLanguage,
  VisualizerPayload,
} from '@/features/algorithm-visualization/types'

export function useVisualizerState() {
  const language = ref<CodeLanguage>(DEFAULT_VISUALIZER_LANGUAGE)
  const code = ref(getDefaultVisualizerCode(DEFAULT_VISUALIZER_LANGUAGE))
  const input = ref(DEFAULT_VISUALIZER_INPUT)
  const payload = ref<VisualizerPayload | null>(null)
  const generating = ref(false)
  const generationSource = ref<'api' | 'mock' | null>(null)
  const generationMessage = ref('')
  const syncedWithExample = ref(true)

  watch(language, (nextLanguage) => {
    if (syncedWithExample.value) {
      code.value = getDefaultVisualizerCode(nextLanguage)
    }
  })

  function useExample() {
    code.value = getDefaultVisualizerCode(language.value)
    input.value = DEFAULT_VISUALIZER_INPUT
    syncedWithExample.value = true
  }

  function clearCode() {
    code.value = ''
    syncedWithExample.value = false
  }

  function clearInput() {
    input.value = ''
  }

  function markCustomEditing() {
    syncedWithExample.value = false
  }

  async function generate() {
    generating.value = true

    // Fast path: example code is unmodified — use frontend mock instantly (no subprocess overhead)
    if (syncedWithExample.value) {
      try {
        const params = { language: language.value, code: code.value, input: input.value }
        payload.value = createBubbleSortPayload(params)
        generationSource.value = 'mock'
        generationMessage.value = '示例代码已使用前端快速预览。'
        toast.success('示例代码可视化已就绪！')
      } finally {
        generating.value = false
      }
      return
    }

    try {
      const result = await resolveVisualizerPayload({
        language: language.value,
        code: code.value,
        input: input.value,
      })

      payload.value = result.payload
      generationSource.value = result.source
      generationMessage.value = result.message

      if (result.source === 'mock') {
        toast.warning(result.message)
      } else {
        toast.success('自定义算法代码执行成功，可视化步骤已载入！')
      }
    } catch (e: any) {
      toast.error(e?.message || '算法生成失败，请检查沙箱编译状态或代码语法。')
    } finally {
      generating.value = false
    }
  }

  function resetAll() {
    language.value = DEFAULT_VISUALIZER_LANGUAGE
    code.value = getDefaultVisualizerCode(DEFAULT_VISUALIZER_LANGUAGE)
    input.value = DEFAULT_VISUALIZER_INPUT
    payload.value = null
    generating.value = false
    generationSource.value = null
    generationMessage.value = ''
    syncedWithExample.value = true
  }

  return {
    language,
    code,
    input,
    payload,
    generating,
    generationSource,
    generationMessage,
    useExample,
    clearCode,
    clearInput,
    markCustomEditing,
    generate,
    resetAll,
  }
}
