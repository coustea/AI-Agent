<template>
  <section class="visualizer-left">
    <header class="visualizer-header">
      <div class="visualizer-title">
        <h2>{{ selectedAlgorithm?.name || '算法可视化' }}</h2>
        <p>{{ selectedAlgorithmDescription }}</p>
      </div>

      <div class="visualizer-state">
        <span :class="['state-dot', { active: hasEvents }]"></span>
        <span>{{ visualizerStatusText }}</span>
      </div>
    </header>

    <section class="visualizer-canvas">
      <div
        v-if="generating"
        class="canvas-loading"
      >
        <div class="loading-spinner"></div>
        <p>正在运行算法代码...</p>
      </div>

      <component
        :is="activeVisualizer"
        v-else-if="hasEvents"
        :current-event="currentEvent"
        :current-step-index="currentStepIndex"
        :events="events"
        :key="`${visualizerType}-${runVersion}`"
      />

      <div
        v-else
        class="visualizer-empty-state"
      >
        <div class="empty-preview">
          <div class="preview-bars">
            <div
              v-for="bar in previewBars"
              :key="bar.index"
              class="preview-bar-item"
            >
              <span class="preview-bar-value">{{ bar.value }}</span>
              <div
                class="preview-bar"
                :style="{ height: `${bar.height}px` }"
              />
              <span class="preview-bar-index">{{ bar.index }}</span>
            </div>
          </div>
        </div>

        <div class="empty-copy">
          <h2>准备好后，开始运行可视化</h2>
          <p>选择模板或编写代码，运行后会在这里逐步展示执行过程。</p>
        </div>
      </div>
    </section>

    <section class="visualizer-control-bar">
      <div class="control-actions">
        <button
          class="control-btn primary"
          :disabled="generating || (!hasEvents && runDisabled)"
          @click="$emit('primary')"
        >
          <component
            :is="primaryIcon"
            :class="['btn-icon', { spin: generating }]"
          />
          <span>{{ primaryLabel }}</span>
        </button>
      </div>

      <div
        v-if="hasEvents"
        class="timeline-meter"
      >
        <span class="step-count">{{ currentStepIndex + 1 }} / {{ events.length }}</span>
        <div class="progress-track">
          <div
            class="progress-fill"
            :style="{ width: progressPercent }"
          />
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { Loader2, Pause, Play } from 'lucide-vue-next'
import type {
  AlgorithmInfo,
  TraceEvent,
  VisualizerType,
} from '@/features/algorithm-visualization/types'
import {
  getAlgorithmDescription,
  getDomainLabel,
} from '@/features/algorithm-visualization/data/visualizerMetadata'
import ArrayBarsVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/sorting/ArrayBarsVisualizer.vue'
import StackQueueVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/structures/StackQueueVisualizer.vue'
import LinkedListVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/structures/LinkedListVisualizer.vue'
import TreeVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/trees/TreeVisualizer.vue'
import GraphVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/graphs/GraphVisualizer.vue'
import DpTableVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/dp/DpTableVisualizer.vue'

const props = defineProps<{
  selectedAlgorithm: AlgorithmInfo | null
  visualizerType: VisualizerType
  events: TraceEvent[]
  currentEvent: TraceEvent | null
  currentStepIndex: number
  generating: boolean
  runVersion: number
  playing: boolean
  finished: boolean
  runDisabled?: boolean
}>()

defineEmits<{
  primary: []
}>()

// 可视化器组件映射表（按可视化器类型选择对应组件）
const visualizerComponents: Record<VisualizerType, Component> = {
  array: ArrayBarsVisualizer,
  'stack-queue': StackQueueVisualizer,
  'linked-list': LinkedListVisualizer,
  tree: TreeVisualizer,
  graph: GraphVisualizer,
  'dp-table': DpTableVisualizer,
}

// 空状态占位柱状图数据
const previewBars = [
  { index: 0, value: 49, height: 76 },
  { index: 1, value: 38, height: 58 },
  { index: 2, value: 65, height: 104 },
  { index: 3, value: 97, height: 148 },
  { index: 4, value: 76, height: 120 },
  { index: 5, value: 13, height: 34 },
]

// 是否有事件数据、当前激活的可视化器组件
const hasEvents = computed(() => props.events.length > 0)
const activeVisualizer = computed(() => visualizerComponents[props.visualizerType])

// 算法描述文本
const selectedAlgorithmDescription = computed(() => {
  if (!props.selectedAlgorithm) {
    return '运行代码后，系统会根据后端返回的轨迹展示算法执行过程。'
  }

  return getAlgorithmDescription(
    getDomainLabel(props.selectedAlgorithm.domain),
    props.selectedAlgorithm.name,
  )
})

// 可视化器状态文本
const visualizerStatusText = computed(() => {
  if (props.generating) return '运行中'
  if (hasEvents.value) return `${props.events.length} 个轨迹步骤`
  return '未运行'
})

// 播放进度百分比
const progressPercent = computed(() => {
  if (!hasEvents.value) return '0%'
  return `${(((props.currentStepIndex + 1) / props.events.length) * 100).toFixed(1)}%`
})

// 主操作按钮的文字标签
const primaryLabel = computed(() => {
  if (props.generating) return '正在生成可视化'
  if (!hasEvents.value) return '运行可视化'
  if (props.playing) return '暂停展示'
  if (props.finished) return '重新展示'
  return '开始展示'
})

// 主操作按钮的图标
const primaryIcon = computed(() => {
  if (props.generating) return Loader2
  return props.playing ? Pause : Play
})
</script>

<style scoped>
.visualizer-left {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
}

.visualizer-header {
  min-height: 64px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.visualizer-title {
  min-width: 0;
}

.visualizer-title h2 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 16px;
  line-height: 1.25;
  font-weight: 900;
}

.visualizer-title p {
  max-width: 760px;
  margin: 3px 0 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.visualizer-state {
  flex: 0 0 auto;
  height: 30px;
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

.visualizer-canvas {
  position: relative;
  flex: 1 1 0%;
  min-height: 0;
  overflow: hidden;
  background:
    linear-gradient(rgba(70, 184, 180, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(70, 184, 180, 0.08) 1px, transparent 1px),
    var(--color-bg);
  background-size: 28px 28px;
}

.canvas-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-content: center;
  gap: 14px;
  background: color-mix(in srgb, var(--color-surface) 92%, transparent);
}

.canvas-loading p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 800;
}

.loading-spinner {
  width: 34px;
  height: 34px;
  margin: 0 auto;
  border: 3px solid rgba(70, 184, 180, 0.16);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

.visualizer-empty-state {
  height: 100%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 20px;
  padding: 24px;
  text-align: center;
}

.empty-preview {
  width: min(560px, 92%);
  height: 180px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-surface) 72%, transparent);
}

.preview-bars {
  height: 150px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 22px;
}

.preview-bar-item {
  width: 46px;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 6px;
}

.preview-bar-value,
.preview-bar-index {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 800;
}

.preview-bar {
  width: 34px;
  border: 1px solid var(--color-primary-border);
  border-radius: 4px 4px 0 0;
  background: linear-gradient(180deg, rgba(70, 184, 180, 0.36), rgba(70, 184, 180, 0.16));
}

.empty-copy {
  max-width: 520px;
}

.empty-copy h2 {
  margin: 0 0 6px;
  color: var(--color-text-strong);
  font-size: 18px;
  line-height: 1.3;
  font-weight: 900;
}

.empty-copy p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.7;
}

.visualizer-control-bar {
  min-height: 50px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.control-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
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

.timeline-meter {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.step-count {
  min-width: 52px;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.progress-track {
  width: min(420px, 42vw);
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-border-light);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
  transition: width 0.3s ease;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-spinner,
  .spin {
    animation-duration: 0.01ms;
    animation-iteration-count: 1;
  }

  .progress-fill {
    transition: none;
  }
}

@media (max-width: 960px) {
  .visualizer-left {
    min-height: 560px;
    border-right: 0;
  }
}

@media (max-width: 768px) {
  .visualizer-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .visualizer-control-bar {
    align-items: stretch;
    flex-direction: column;
    flex-wrap: wrap;
    padding: 8px 12px;
  }

  .control-actions,
  .timeline-meter {
    width: 100%;
  }

  .progress-track {
    width: 100%;
  }

  .empty-copy h2 {
    font-size: 16px;
  }

  .empty-preview {
    display: none;
  }
}
</style>
