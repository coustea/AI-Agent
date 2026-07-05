<template>
  <section class="visualizer-canvas">
    <div v-if="generating" class="canvas-loading">
      <div class="loading-spinner"></div>
      <p>正在生成可视化步骤...</p>
    </div>

    <ArrayBarsVisualizer
      v-else-if="payload?.visualizerType === 'array' || payload?.visualizerType === '1D_ARRAY'"
      :initial-state="payload.initialState as ArrayVisualizerState"
      :current-step="currentStep"
      :current-step-index="currentStepIndex"
    />

    <GraphVisualizer
      v-else-if="payload?.visualizerType === 'graph' || payload?.visualizerType === 'GRAPH'"
      :initial-state="payload.initialState"
      :current-step="currentStep"
      :current-step-index="currentStepIndex"
    />

    <TreeVisualizer
      v-else-if="payload?.visualizerType === 'tree' || payload?.visualizerType === 'TREE'"
      :initial-state="payload.initialState"
      :current-step="currentStep"
      :current-step-index="currentStepIndex"
    />

    <VisualizerEmptyState v-else />
  </section>
</template>

<script setup lang="ts">
import VisualizerEmptyState from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerEmptyState.vue'
import ArrayBarsVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/ArrayBarsVisualizer.vue'
import GraphVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/GraphVisualizer.vue'
import TreeVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/TreeVisualizer.vue'
import type {
  ArrayVisualizerState,
  VisualizerPayload,
  VisualStep,
} from '@/features/algorithm-visualization/types'

defineProps<{
  payload: VisualizerPayload | null
  currentStep: VisualStep | null
  currentStepIndex: number
  generating: boolean
}>()
</script>

<style scoped>
.visualizer-canvas {
  position: relative;
  min-height: 0;
  border-radius: 22px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
}

.canvas-loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 14px;
  background: rgba(248, 250, 252, 0.85);
  z-index: 2;
}

.canvas-loading p {
  margin: 0;
  font-size: 14px;
  color: #475569;
}

.loading-spinner {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 3px solid rgba(37, 99, 235, 0.16);
  border-top-color: #2563eb;
  animation: spin 0.9s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
