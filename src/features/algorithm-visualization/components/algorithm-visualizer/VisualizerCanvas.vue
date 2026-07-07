<template>
  <section class="visualizer-canvas">
    <div v-if="generating" class="canvas-loading">
      <div class="loading-spinner"></div>
      <p>正在运行算法代码...</p>
    </div>

    <ArrayBarsVisualizer
      v-else-if="visualizerType === 'array'"
      :current-event="currentEvent"
      :current-step-index="currentStepIndex"
      :events="events"
    />

    <StackQueueVisualizer
      v-else-if="visualizerType === 'stack-queue'"
      :current-event="currentEvent"
      :current-step-index="currentStepIndex"
      :events="events"
    />

    <LinkedListVisualizer
      v-else-if="visualizerType === 'linked-list'"
      :current-event="currentEvent"
      :current-step-index="currentStepIndex"
      :events="events"
    />

    <TreeVisualizer
      v-else-if="visualizerType === 'tree'"
      :current-event="currentEvent"
      :current-step-index="currentStepIndex"
      :events="events"
    />

    <GraphVisualizer
      v-else-if="visualizerType === 'graph'"
      :current-event="currentEvent"
      :current-step-index="currentStepIndex"
      :events="events"
    />

    <DpTableVisualizer
      v-else-if="visualizerType === 'dp-table'"
      :current-event="currentEvent"
      :current-step-index="currentStepIndex"
      :events="events"
    />

    <VisualizerEmptyState v-else />
  </section>
</template>

<script setup lang="ts">
import VisualizerEmptyState from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerEmptyState.vue'
import ArrayBarsVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/ArrayBarsVisualizer.vue'
import StackQueueVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/StackQueueVisualizer.vue'
import LinkedListVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/LinkedListVisualizer.vue'
import TreeVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/TreeVisualizer.vue'
import GraphVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/GraphVisualizer.vue'
import DpTableVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/DpTableVisualizer.vue'
import type { TraceEvent, VisualizerType } from '@/features/algorithm-visualization/types'

defineProps<{
  events: TraceEvent[]
  currentEvent: TraceEvent | null
  currentStepIndex: number
  visualizerType: VisualizerType
  generating: boolean
}>()
</script>

<style scoped>
.visualizer-canvas {
  position: relative;
  flex: 1 1 0%;
  min-height: 0;
  overflow: hidden;
  background: #ffffff;
}

.canvas-loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 14px;
  background: rgba(255, 255, 255, 0.95);
  z-index: 2;
}

.canvas-loading p {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 3px solid rgba(70, 184, 180, 0.16);
  border-top-color: var(--color-primary);
  animation: spin 0.9s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
