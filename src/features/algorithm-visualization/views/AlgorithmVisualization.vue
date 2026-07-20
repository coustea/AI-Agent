<template>
  <main class="algorithm-visualizer-page">
    <header class="workspace-toolbar">
      <div class="toolbar-left">
        <div class="workspace-identity">
          <span class="workspace-kicker">学习工作台</span>
          <strong>算法可视化</strong>
        </div>

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
      </div>

      <div class="toolbar-actions">
        <div class="visualizer-state">
          <span :class="['state-dot', { active: hasEvents }]"></span>
          <span>{{ visualizerStatusText }}</span>
        </div>

        <button
          class="control-btn primary"
          :disabled="generating || (!hasEvents && runDisabled)"
          @click="handlePrimaryAction"
        >
          <component
            :is="primaryIcon"
            :class="['btn-icon', { spin: generating }]"
          />
          <span>{{ primaryLabel }}</span>
        </button>

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
        :on-step-complete="handleStepComplete"
      />

      <aside class="visualizer-right">
        <div class="editor-tabs">
          <button
            type="button"
            class="editor-tab-btn"
            :class="{ active: activeEditorTab === 'code' }"
            @click="setEditorTab('code')"
          >
            <Code2 class="tab-icon" />
            代码
          </button>
          <button
            type="button"
            class="editor-tab-btn"
            :class="{ active: activeEditorTab === 'input' }"
            @click="setEditorTab('input')"
          >
            <Settings class="tab-icon" />
            输入数据
          </button>
        </div>

        <div class="editor-content">
          <AlgorithmCodeEditorPanel
            ref="codeEditorRef"
            v-show="activeEditorTab === 'code'"
            :model-value="code"
            title="官方模板代码"
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
import { Code2, Settings, Loader2, Pause, Play } from 'lucide-vue-next'
import type { RunError } from '@/features/algorithm-visualization/types'
import AlgorithmTemplatePicker from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmTemplatePicker.vue'
import AlgorithmVisualizerStage from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmVisualizerStage.vue'
import AlgorithmCodeEditorPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmCodeEditorPanel.vue'
import AlgorithmInputDataPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmInputDataPanel.vue'
import AlgorithmRunErrorDialog from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmRunErrorDialog.vue'
import { useAnimationOrchestrator } from '@/features/algorithm-visualization/composables/useAnimationOrchestrator'
import { useAlgorithmTemplate } from '@/features/algorithm-visualization/composables/useAlgorithmTemplate'
import { useAlgorithmRun } from '@/features/algorithm-visualization/composables/useAlgorithmRun'
import {
  getDomainLabel,
  getVisualizerLabel,
  groupAlgorithmsByDomain,
} from '@/features/algorithm-visualization/data/visualizerMetadata'

defineOptions({
  name: 'AlgorithmVisualization',
})

// 算法模板状态（算法 key、执行源码与输入契约）。
const {
  algorithm,
  code,
  loading,
  algorithms,
  metaLoading,
  currentAlgorithm,
  templateData,
  loadMeta,
  loadTemplate,
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

// 代码编辑器模板引用（用于命令式调用 highlightLine）
const codeEditorRef = ref<InstanceType<typeof AlgorithmCodeEditorPanel> | null>(null)

// 统一动画编排器 — 替代 useTracePlayer + useVisualizerTimeline
const orchestrator = useAnimationOrchestrator({
  events: () => events.value,
  onStepChange(event) {
    // 同步 Monaco 行高亮
    codeEditorRef.value?.highlightLine(event?.line)
  },
})

const errorDialogOpen = ref(false)
const activeEditorTab = ref<'code' | 'input'>('code')
const inputDataJson = ref<Record<string, unknown>>({})
const inputDataValid = ref(true)

// 当前事件和步骤索引
const currentEvent = computed(() => orchestrator.currentEvent.value)
const currentStepIndex = computed(() => orchestrator.currentStepIndex.value)

// 按领域分组的算法分类
const algorithmCategoryGroups = computed(() => groupAlgorithmsByDomain(algorithms.value))

// 当前领域和可视化类型的中文标签
const selectedCategoryLabel = computed(() => {
  return currentAlgorithm.value ? getDomainLabel(currentAlgorithm.value.domain) : '算法分类'
})
const selectedVisualLabel = computed(() => {
  return getVisualizerLabel(currentAlgorithm.value?.visualizerType)
})

// 当前可视化器类型（优先取事件中指定，其次算法默认）
const resolvedVisualizerType = computed(() => {
  return currentEvent.value?.visualizerType ?? currentAlgorithm.value?.visualizerType ?? getCurrentVisualizerType()
})

// 当前算法的默认输入数据
const currentAlgorithmDefaultData = computed(() => {
  return templateData.value?.defaultInput ?? {}
})

const hasEvents = computed(() => events.value.length > 0)

const visualizerStatusText = computed(() => {
  if (generating.value) return '运行中'
  if (hasEvents.value) return `${events.value.length} 个轨迹步骤`
  return '未运行'
})

const primaryLabel = computed(() => {
  if (generating.value) return '正在生成...'
  if (!hasEvents.value) return '运行可视化'
  if (orchestrator.playing.value) return '暂停展示'
  if (orchestrator.finished.value) return '重新展示'
  return '开始展示'
})

const primaryIcon = computed(() => {
  if (generating.value) return Loader2
  return orchestrator.playing.value ? Pause : Play
})

const runDisabled = computed(() => {
  return loading.value || !inputDataValid.value
})

const currentAlgorithmInputSchema = computed(() => {
  return templateData.value?.inputSchema
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

function setEditorTab(tab: 'code' | 'input') {
  activeEditorTab.value = tab
}

// 唯一主操作：首次运行，之后控制播放。
async function handlePrimaryAction() {
  if (generating.value) return
  if (!events.value.length) {
    await handleRun()
    return
  }
  if (orchestrator.playing.value) {
    orchestrator.pause()
    return
  }
  orchestrator.play()
}

// 可视化器动画完成回调 — 通知编排器
function handleStepComplete() {
  orchestrator.notifyStepComplete()
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
  await runAlgorithm({
    algorithm: algorithm.value,
    inputData: inputDataJson.value,
  })
  // 运行完成后重置编排器并自动播放
  orchestrator.reset()
  if (events.value.length > 0) {
    orchestrator.play()
  }
}

function showRunError(error: RunError) {
  runError.value = error
  errorDialogOpen.value = true
}

function discardVisualization() {
  orchestrator.reset()
  clearRun()
}

watch(inputDataJson, () => {
  if (!generating.value) discardVisualization()
}, { deep: true })
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

.toolbar-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.reset-btn {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: var(--radius-sm) !important;
  font-size: 12px;
  font-weight: 900;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  transition: var(--btn-transition);
}

.reset-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-text-strong);
}

.visualizer-state {
  flex: 0 0 auto;
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 900;
}

.state-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-text-faint);
}

.state-dot.active {
  background: var(--color-primary);
}

.control-btn {
  height: 32px;
  min-width: 104px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
  transition: var(--btn-transition);
}

.control-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: var(--color-surface-hover);
}

.control-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.control-btn.primary {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
}

.control-btn.primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
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
