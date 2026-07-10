<template>
  <main class="algorithm-visualizer-page">
    <header class="workspace-toolbar">
      <div class="toolbar-left">
        <AlgorithmTemplatePicker
          :categories="algorithmCategoryGroups"
          :selected-algorithm="currentAlgorithm"
          :selected-algorithm-key="algorithm"
          :selected-category-label="selectedCategoryLabel"
          :selected-visual-label="selectedVisualLabel"
          :disabled="generating"
          :meta-loading="metaLoading"
          @select="selectTemplate"
        />

        <div class="template-summary">
          <span class="summary-title">{{ selectedCategoryLabel }}</span>
          <span class="summary-divider"></span>
          <span class="summary-text">{{ selectedVisualLabel }}</span>
        </div>
      </div>

      <div class="toolbar-actions">
        <Button
          variant="outline"
          class="reset-btn"
          :disabled="generating || loading"
          @click="resetTemplate"
        >
          <RotateCcw class="btn-icon" />
          重置模板
        </Button>

        <Button
          class="run-btn"
          :disabled="generating || loading || !code.trim()"
          @click="handleRun"
        >
          <Play
            v-if="!generating"
            class="btn-icon"
          />
          <Loader2
            v-else
            class="btn-icon spin"
          />
          {{ generating ? '运行中...' : '运行可视化' }}
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
        :playing="playback.playing.value"
        :finished="playback.finished.value"
        @primary="handlePrimaryAction"
        @reset="playback.reset"
      />

      <aside class="visualizer-right">
        <AlgorithmCodeEditorPanel
          v-model="code"
          v-model:language="editorLanguageModel"
          :languages="supportedEditorLanguages"
          :disabled="generating || loading"
          :active-line="currentEvent?.line"
          :current-step-message="currentEvent?.message"
          :current-step-index="currentStepIndex"
          :event-count="events.length"
          :generating="generating"
        />
      </aside>
    </section>

    <AlgorithmRunErrorDialog
      v-model:open="errorDialogOpen"
      :error="runError"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Loader2, Play, RotateCcw } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import type { CodeLanguage } from '@/features/algorithm-visualization/types'
import AlgorithmTemplatePicker from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmTemplatePicker.vue'
import AlgorithmVisualizerStage from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmVisualizerStage.vue'
import AlgorithmCodeEditorPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmCodeEditorPanel.vue'
import AlgorithmRunErrorDialog from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmRunErrorDialog.vue'
import { useTracePlayer } from '@/features/algorithm-visualization/composables/useTracePlayer'
import { useAlgorithmTemplate } from '@/features/algorithm-visualization/composables/useAlgorithmTemplate'
import { useAlgorithmRun } from '@/features/algorithm-visualization/composables/useAlgorithmRun'
import { useVisualizerTimeline } from '@/features/algorithm-visualization/composables/useVisualizerTimeline'
import {
  getDomainLabel,
  getVisualizerLabel,
  groupAlgorithmsByDomain,
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
  run: runAlgorithm,
} = useAlgorithmRun()

// 步骤播放器
const playback = useTracePlayer(() => events.value)
const errorDialogOpen = ref(false)

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

// 编辑器语言双向绑定（运行中禁止切换）
const editorLanguageModel = computed({
  get: () => language.value,
  set: (value: CodeLanguage) => {
    if (generating.value) return
    language.value = value
  },
})

// 当前可视化器类型（优先取事件中指定，其次算法默认）
const resolvedVisualizerType = computed(() => {
  return currentEvent.value?.visualizerType ?? currentAlgorithm.value?.visualizerType ?? getCurrentVisualizerType()
})

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
function selectTemplate(algorithmKey: string) {
  if (generating.value) return
  const beforeAlgorithm = algorithm.value
  const beforeLanguage = language.value
  setAlgorithm(algorithmKey)
  // 如果算法和语言未变但需重新加载（同一算法再次点选）
  if (beforeAlgorithm === algorithm.value && beforeLanguage === language.value) {
    loadTemplate()
  }
}

// 主操作按钮：播放/暂停切换
function handlePrimaryAction() {
  if (!events.value.length) return
  if (playback.playing.value) {
    playback.pause()
    return
  }
  playback.play()
}

// 运行算法可视化
async function handleRun() {
  if (generating.value || !code.value.trim()) return
  const selected = currentAlgorithm.value
  await runAlgorithm({
    domain: selected?.domain ?? 'all',
    algorithm: algorithm.value,
    visualizerType: selected?.visualizerType ?? getCurrentVisualizerType(),
    language: language.value,
    code: code.value,
  })
  // 运行完成后重置播放器并自动播放
  playback.reset()
  if (events.value.length > 0) {
    playback.play()
  }
}
</script>

<style scoped>
.algorithm-visualizer-page {
  height: calc(100vh - var(--navbar-height, 72px));
  min-height: 680px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-surface);
}

.workspace-toolbar {
  min-height: 58px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.toolbar-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 18px;
}

.template-summary {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.summary-title {
  color: var(--color-text-secondary);
  font-weight: 900;
}

.summary-divider {
  width: 1px;
  height: 14px;
  background: var(--color-border);
}

.summary-text {
  overflow: hidden;
  text-overflow: ellipsis;
}

.toolbar-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.reset-btn,
.run-btn {
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

.run-btn {
  padding: 0 16px;
  border: 0;
  background: var(--color-primary);
  color: #ffffff;
}

.run-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

.algorithm-visualizer-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 6fr) minmax(0, 4fr);
  gap: 1px;
  background: var(--color-border);
}

.visualizer-right {
  min-width: 0;
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

  .template-summary {
    display: none;
  }
}

@media (max-width: 960px) {
  .algorithm-visualizer-page {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .algorithm-visualizer-main {
    grid-template-columns: 1fr;
  }

  .visualizer-right {
    min-height: 520px;
  }
}

@media (max-width: 768px) {
  .workspace-toolbar {
    padding: 8px 12px;
  }

  .toolbar-actions {
    flex-wrap: wrap;
  }

  .reset-btn,
  .run-btn {
    flex: 1;
  }
}
</style>
