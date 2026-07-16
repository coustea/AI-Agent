<template>
  <main class="algorithm-visualizer-page">
    <header class="workspace-toolbar">
      <div class="toolbar-left">
        <div class="workspace-identity">
          <span class="workspace-kicker">学习工作台</span>
          <strong>算法可视化</strong>
        </div>

        <div class="execution-mode-switch">
          <button
            type="button"
            aria-label="切换到官方算法模板"
            :class="{ active: executionMode === 'official' }"
            :disabled="generating"
            @click="setExecutionMode('official')"
          >官方模板</button>
          <button
            type="button"
            aria-label="切换到自定义代码"
            :class="{ active: executionMode === 'custom' }"
            :disabled="generating"
            @click="setExecutionMode('custom')"
          >自定义代码</button>
        </div>

        <AlgorithmTemplatePicker
          v-if="executionMode === 'official'"
          :categories="algorithmCategoryGroups"
          :selected-algorithm="currentAlgorithm"
          :selected-algorithm-key="algorithm"
          :selected-category-label="selectedCategoryLabel"
          :selected-visual-label="selectedVisualLabel"
          :disabled="generating"
          :meta-loading="metaLoading"
          @select="selectTemplate"
        />

        <label
          v-else
          class="custom-visualizer-select"
        >
          可视化类型
          <select v-model="customVisualizerType">
            <option
              v-for="type in visualizerTypes"
              :key="type"
              :value="type"
            >{{ getVisualizerLabel(type) }}</option>
          </select>
        </label>

        <label
          v-if="executionMode === 'custom' && customContract"
          class="custom-visualizer-select"
        >
          入口函数
          <select
            v-model="customEntryFunction"
            :disabled="generating || customContractLoading"
          >
            <option
              v-for="item in customContract.functions"
              :key="item.name"
              :value="item.name"
            >{{ item.name }}({{ item.parameters.join(', ') }})</option>
          </select>
        </label>

      </div>

      <div class="toolbar-actions">
        <Button
          v-if="executionMode === 'custom'"
          variant="outline"
          class="reset-btn"
          :disabled="generating || loading"
          @click="handleReset"
        >
          <RotateCcw class="btn-icon" />
          恢复示例代码
        </Button>
      </div>
    </header>

    <section class="algorithm-visualizer-main">
      <AlgorithmVisualizerStage
        :selected-algorithm="currentAlgorithm"
        :visualizer-type="resolvedVisualizerType"
        :events="events"
        :current-event="currentEvent"
        :current-step-index="currentStepIndex"
        :generating="generating"
        :run-version="runVersion"
        :playing="playback.playing.value"
        :finished="playback.finished.value"
        :run-disabled="loading || !inputDataValid || customContractLoading"
        @primary="handlePrimaryAction"
      />

      <aside class="visualizer-right">
        <div class="editor-tabs">
          <button
            type="button"
            class="editor-tab-btn"
            :class="{ active: activeEditorTab === 'code' }"
            @click="activeEditorTab = 'code'"
          >
            <Code2 class="tab-icon" />
            代码
          </button>
          <button
            type="button"
            class="editor-tab-btn"
            :class="{ active: activeEditorTab === 'input' }"
            @click="activeEditorTab = 'input'"
          >
            <Settings class="tab-icon" />
            输入数据
          </button>
        </div>

        <div class="editor-content">
          <AlgorithmCodeEditorPanel
            v-show="activeEditorTab === 'code'"
            :model-value="editorCode"
            :title="executionMode === 'official' ? '官方模板代码' : '自定义 Python 代码'"
            :readonly="executionMode === 'official'"
            @update:model-value="updateEditorCode"
            :language="language"
            :languages="supportedEditorLanguages"
            :disabled="generating || loading"
            :active-line="currentEvent?.line"
            :current-step-message="currentEvent?.message"
            :current-step-index="currentStepIndex"
            :event-count="events.length"
            :generating="generating"
          />

          <AlgorithmInputDataPanel
            v-show="activeEditorTab === 'input'"
            v-model="inputDataJson"
            :disabled="generating || loading"
            :default-data="currentAlgorithmDefaultData"
            :input-schema="currentAlgorithmInputSchema"
            @validity-change="inputDataValid = $event"
          />
        </div>
      </aside>
    </section>

    <AlgorithmRunErrorDialog
      v-if="errorDialogOpen && runError"
      v-model:open="errorDialogOpen"
      :error="runError"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Code2, RotateCcw, Settings } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { getErrorMessage } from '@/shared/api/http'
import type { CustomCodeContract, RunError, VisualizerType } from '@/features/algorithm-visualization/types'
import AlgorithmTemplatePicker from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmTemplatePicker.vue'
import AlgorithmVisualizerStage from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmVisualizerStage.vue'
import AlgorithmCodeEditorPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmCodeEditorPanel.vue'
import AlgorithmInputDataPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmInputDataPanel.vue'
import AlgorithmRunErrorDialog from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmRunErrorDialog.vue'
import { useTracePlayer } from '@/features/algorithm-visualization/composables/useTracePlayer'
import { useAlgorithmTemplate } from '@/features/algorithm-visualization/composables/useAlgorithmTemplate'
import { useAlgorithmRun } from '@/features/algorithm-visualization/composables/useAlgorithmRun'
import { useVisualizerTimeline } from '@/features/algorithm-visualization/composables/useVisualizerTimeline'
import { fetchCustomCodeContract } from '@/features/algorithm-visualization/api/algorithmVisualizer'
import {
  getDomainLabel,
  getVisualizerLabel,
  groupAlgorithmsByDomain,
  VISUALIZER_LABELS,
} from '@/features/algorithm-visualization/data/visualizerMetadata'

defineOptions({
  name: 'AlgorithmVisualization',
})

// 算法模板状态（语言、算法 key、代码、算法信息等）
const {
  language,
  algorithm,
  code,
  loading,
  languages,
  algorithms,
  metaLoading,
  currentAlgorithm,
  templateData,
  loadMeta,
  loadTemplate,
  resetTemplate,
  setAlgorithm,
  getCurrentVisualizerType,
} = useAlgorithmTemplate()

// 运行状态（事件列表、错误信息、生成中标志）
const {
  events,
  runError,
  generating,
  runVersion,
  run: runAlgorithm,
  clear: clearRun,
} = useAlgorithmRun()

// 步骤播放器
const playback = useTracePlayer(() => events.value)
const errorDialogOpen = ref(false)
const executionMode = ref<'official' | 'custom'>('official')
const activeEditorTab = ref<'code' | 'input'>('code')
const inputDataJson = ref<Record<string, unknown>>({})
const inputDataValid = ref(true)
const customCode = ref(`def bubble_sort(values):
  arr = list(values)
  for end in range(len(arr) - 1, 0, -1):
    for index in range(end):
      if arr[index] > arr[index + 1]:
        arr[index], arr[index + 1] = arr[index + 1], arr[index]
  return arr
`)
const defaultCustomCode = customCode.value
const customVisualizerType = ref<VisualizerType>('array')
const visualizerTypes = Object.keys(VISUALIZER_LABELS) as VisualizerType[]
const customContract = ref<CustomCodeContract | null>(null)
const customContractLoading = ref(false)
const customContractStale = ref(true)
const customEntryFunction = ref('')

// 自动播放时间线调度
useVisualizerTimeline({
  playing: playback.playing,
  currentEvent: playback.currentEvent,
  next: playback.next,
  pause: playback.pause,
})

// 当前事件和步骤索引
const currentEvent = computed(() => playback.currentEvent.value)
const currentStepIndex = computed(() => playback.currentStepIndex.value)
const editorCode = computed(() => executionMode.value === 'official' ? code.value : customCode.value)

// 按领域分组的算法分类
const algorithmCategoryGroups = computed(() => groupAlgorithmsByDomain(algorithms.value))

// 当前领域和可视化类型的中文标签
const selectedCategoryLabel = computed(() => {
  return currentAlgorithm.value ? getDomainLabel(currentAlgorithm.value.domain) : '算法分类'
})
const selectedVisualLabel = computed(() => {
  return getVisualizerLabel(currentAlgorithm.value?.visualizerType)
})

// 编辑器支持的语言列表（过滤掉当前算法不支持的语言）
const supportedEditorLanguages = computed(() => {
  const selected = currentAlgorithm.value
  if (!selected?.supportedLanguages.length) {
    return languages.value
  }
  const filtered = languages.value.filter((item) => selected.supportedLanguages.includes(item.key))
  return filtered.length > 0 ? filtered : languages.value
})

// 当前可视化器类型（优先取事件中指定，其次算法默认）
const resolvedVisualizerType = computed(() => {
  return currentEvent.value?.visualizerType ?? (executionMode.value === 'custom'
    ? customVisualizerType.value
    : currentAlgorithm.value?.visualizerType ?? getCurrentVisualizerType())
})

// 当前算法的默认输入数据
const currentAlgorithmDefaultData = computed(() => {
  return executionMode.value === 'custom' ? customContract.value?.defaultInput ?? {} : templateData.value?.defaultInput ?? {}
})

const currentAlgorithmInputSchema = computed(() => {
  return executionMode.value === 'custom' ? customContract.value?.inputSchema : templateData.value?.inputSchema
})

// 模板数据变化时，更新输入数据
watch(
  () => templateData.value?.defaultInput,
  (newData) => {
    if (newData) {
      inputDataJson.value = newData
    }
  },
  { immediate: true },
)

// 运行出错时自动打开错误弹窗
watch(
  () => runError.value,
  (error) => {
    if (error) errorDialogOpen.value = true
  },
)

// 初始化加载元数据和代码模板
onMounted(async () => {
  await loadMeta()
  if (!code.value.trim()) {
    await loadTemplate()
  }
})

// 选择算法模板
async function selectTemplate(algorithmKey: string) {
  if (generating.value) return
  discardVisualization()
  await setAlgorithm(algorithmKey)
}

function setExecutionMode(mode: 'official' | 'custom') {
  executionMode.value = mode
  activeEditorTab.value = 'code'
  discardVisualization()
  inputDataJson.value = structuredClone(mode === 'custom' ? customContract.value?.defaultInput ?? {} : currentAlgorithmDefaultData.value)
  if (mode === 'custom') void refreshCustomContract()
  if (mode === 'official' && !code.value.trim()) void loadTemplate()
}

function updateEditorCode(nextCode: string) {
  if (executionMode.value === 'custom') {
    customCode.value = nextCode
    customEntryFunction.value = ''
    customContractStale.value = true
    discardVisualization()
  }
}

function handleReset() {
  if (executionMode.value === 'custom') {
    customCode.value = defaultCustomCode
    customEntryFunction.value = ''
    customContractStale.value = true
    void refreshCustomContract()
    discardVisualization()
    return
  }
  discardVisualization()
  void resetTemplate()
}

// 唯一主操作：首次运行，之后控制播放。
async function handlePrimaryAction() {
  if (!events.value.length) {
    await handleRun()
    return
  }
  if (playback.playing.value) {
    playback.pause()
    return
  }
  playback.play()
}

// 运行算法可视化
async function handleRun() {
  if (generating.value) return
  if (!inputDataValid.value) {
    activeEditorTab.value = 'input'
    showRunError({
      errorType: 'INPUT_INVALID',
      message: '有输入项格式不正确，请按字段提示修正后再运行。',
    })
    return
  }
  if (executionMode.value === 'custom') {
    const synchronized = await refreshCustomContract()
    if (!synchronized || !inputDataValid.value || !customContract.value) {
      activeEditorTab.value = customContract.value ? 'input' : 'code'
      return
    }
  }
  const params = executionMode.value === 'official'
    ? {
        mode: 'official' as const,
        algorithm: algorithm.value,
        language: language.value,
        inputData: inputDataJson.value,
      }
    : {
        mode: 'custom' as const,
        language: language.value,
        code: customCode.value,
        visualizerType: customVisualizerType.value,
        entryFunction: customEntryFunction.value,
        inputData: inputDataJson.value,
      }
  await runAlgorithm(params)
  // 运行完成后重置播放器并自动播放
  playback.reset()
  if (events.value.length > 0) {
    playback.play()
  }
}

function showRunError(error: RunError) {
  runError.value = error
  errorDialogOpen.value = true
}

function discardVisualization() {
  playback.reset()
  clearRun()
}

async function refreshCustomContract(force = false) {
  if (!customCode.value.trim()) {
    showRunError({
      errorType: 'CUSTOM_CONTRACT_INVALID',
      message: '请先输入一段可执行的 Python 代码。',
    })
    return false
  }
  if (!force && !customContractStale.value && customContract.value && customEntryFunction.value) return true
  customContractLoading.value = true
  try {
    const response = await fetchCustomCodeContract(customCode.value, customEntryFunction.value || undefined)
    const contract = response.data.data
    if (!contract) {
      showRunError({
        errorType: 'CUSTOM_CONTRACT_INVALID',
        message: '未能识别可运行的入口函数，请检查代码后重试。',
      })
      return false
    }
    const previousInput = inputDataJson.value
    customContract.value = contract
    customEntryFunction.value = contract.entryFunction
    inputDataJson.value = Object.fromEntries(
      Object.entries(contract.defaultInput).map(([key, defaultValue]) => [key, key in previousInput ? previousInput[key] : defaultValue]),
    )
    customContractStale.value = false
    inputDataValid.value = true
    return true
  } catch (error) {
    showRunError({
      errorType: 'CUSTOM_CONTRACT_INVALID',
      message: getErrorMessage(error, '未能识别代码的运行参数，请检查函数定义后重试。'),
    })
    return false
  } finally {
    customContractLoading.value = false
  }
}

watch(customEntryFunction, (entryFunction, previousEntryFunction) => {
  if (!entryFunction || entryFunction === previousEntryFunction || !customContract.value || customContractLoading.value) return
  discardVisualization()
  customContractStale.value = true
  void refreshCustomContract()
})

watch(inputDataJson, () => {
  if (!generating.value) discardVisualization()
}, { deep: true })

watch(customVisualizerType, () => {
  if (executionMode.value === 'custom') discardVisualization()
})
</script>

<style scoped>
.algorithm-visualizer-page {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-surface);
}

.workspace-toolbar {
  min-height: 68px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.toolbar-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.workspace-identity {
  min-width: 112px;
  display: grid;
  gap: 1px;
  padding-right: var(--space-4);
  border-right: 1px solid var(--color-border-light);
}

.workspace-kicker {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: var(--weight-semibold);
  letter-spacing: 0.02em;
}

.workspace-identity strong {
  color: var(--color-text-strong);
  font-size: var(--text-md);
  line-height: 1.25;
  font-weight: var(--weight-bold);
}

.execution-mode-switch {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.execution-mode-switch button {
  height: 32px;
  padding: 0 10px;
  border: 0;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.execution-mode-switch button:last-child { border-right: 0; }
.execution-mode-switch button.active {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.execution-mode-switch button:focus-visible,
.custom-visualizer-select select:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 2px;
}

.custom-visualizer-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 800;
}

.custom-visualizer-select select {
  height: 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-strong);
  padding: 0 8px;
}

.toolbar-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.reset-btn {
  height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: var(--radius-sm) !important;
  font-size: 13px;
  font-weight: 900;
}

.reset-btn {
  padding: 0 12px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
}

.reset-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-text-strong);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.algorithm-visualizer-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 56fr) minmax(440px, 44fr);
  background: var(--color-surface);
}

.visualizer-right {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--color-border);
}

.editor-tabs {
  height: 44px;
  flex: 0 0 auto;
  display: flex;
  align-items: stretch;
  gap: 0;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.editor-tab-btn {
  height: 44px;
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 16px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: color 0.18s ease, background-color 0.18s ease, border-color 0.18s ease;
}

.editor-tab-btn:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
}

.editor-tab-btn.active {
  border-bottom-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.tab-icon {
  width: 14px;
  height: 14px;
}

.editor-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--color-surface);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1180px) {
  .workspace-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-left {
    width: 100%;
    flex-wrap: wrap;
    gap: 10px;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .workspace-identity {
    border-right: 0;
    padding-right: 0;
  }

}

@media (max-width: 620px) {
  .workspace-toolbar {
    padding: var(--space-3);
  }

  .toolbar-left {
    align-items: flex-start;
  }

  .execution-mode-switch {
    width: 100%;
  }

  .execution-mode-switch button {
    flex: 1;
  }
}

@media (max-width: 960px) {
  .algorithm-visualizer-page {
    height: auto;
    min-height: 100%;
    overflow: visible;
  }

  .algorithm-visualizer-main {
    grid-template-columns: 1fr;
  }

  .visualizer-right {
    min-height: 520px;
    border-top: 1px solid var(--color-border);
    border-left: 0;
  }
}

@media (max-width: 768px) {
  .workspace-toolbar {
    padding: 8px 12px;
  }

  .toolbar-actions {
    flex-wrap: wrap;
  }

  .reset-btn {
    flex: 1;
  }
}
</style>
