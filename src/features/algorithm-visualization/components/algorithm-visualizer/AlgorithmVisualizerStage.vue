<template>
  <section class="visualizer-left">
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
        :on-step-complete="onStepComplete"
        :key="`${visualizerType}-${runVersion}`"
      />

      <div
        v-else
        class="visualizer-empty-state"
      >
        <div class="empty-preview">
          <span class="preview-label">示例数组</span>
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

    <section v-if="hasEvents" class="visualizer-control-bar">
      <div class="timeline-meter">
        <span class="step-count">{{ currentStepIndex + 1 }} / {{ events.length }}</span>
        <div class="progress-track">
          <div
            class="progress-fill"
            :style="{ transform: `scaleX(${progressScale})` }"
          />
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import type {
  AlgorithmInfo,
  TraceEvent,
  VisualizerType,
} from '@/features/algorithm-visualization/types'
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
  onStepComplete?: () => void
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

// 空状态占位轨迹柱状图数据
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

// 播放进度百分比
const progressScale = computed(() => {
  if (!hasEvents.value) return 0
  return Math.min(1, Math.max(0, (props.currentStepIndex + 1) / props.events.length))
})
</script>

<style scoped>
.visualizer-left {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
}
.visualizer-canvas {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.canvas-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--color-surface);
  z-index: 10;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.visualizer-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 24px;
  text-align: center;
}

.empty-preview {
  width: min(560px, 92%);
  height: 180px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  position: relative;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: var(--shadow-xs);
  margin-bottom: 24px;
}

.preview-label {
  position: absolute;
  top: 12px;
  left: 14px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: var(--weight-semibold);
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

.visualizer-control-bar {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
}

.timeline-meter {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-count {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.progress-track {
  flex: 1;
  height: 4px;
  background: var(--color-border-light);
  border-radius: 2px;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transition: transform 0.2s ease;
  transform-origin: left;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .visualizer-control-bar {
    padding: 8px 12px;
  }

  .empty-preview {
    display: none;
  }
}
</style>
