<template>
  <main class="algorithm-visualizer-page">
    <section class="algorithm-visualizer-main">
      <section class="visualizer-left">
        <VisualizerCanvas
          :payload="payload"
          :current-step="currentStep"
          :current-step-index="currentStepIndex"
          :generating="generating"
        />

        <VisualizerControlBar
          :steps="steps"
          :playing="playing"
          :current-step-index="currentStepIndex"
          :speed="speed"
          :finished="finished"
          @play="play"
          @pause="pause"
          @next="next"
          @prev="prev"
          @reset="resetPlayback"
          @speed-change="setSpeed"
          @seek="seek"
        />
      </section>

      <aside class="visualizer-right">
        <CodeInputPanel
          v-model:code="code"
          v-model:language="language"
          v-model:input="input"
          :loading="generating"
          :active-line="currentStep?.codeLine"
          :finished="finished"
          :execution-label="activeLineLabel"
          @generate="handleGenerate"
          @use-example="handleUseExample"
          @clear="handleClear"
          @reset-all="handleResetAll"
          @dirty="markCustomEditing"
        />
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import CodeInputPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/CodeInputPanel.vue'
import VisualizerCanvas from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerCanvas.vue'
import VisualizerControlBar from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerControlBar.vue'
import { useVisualizerPlayback } from '@/features/algorithm-visualization/composables/useVisualizerPlayback'
import { useVisualizerState } from '@/features/algorithm-visualization/composables/useVisualizerState'
import { useVisualizerTimeline } from '@/features/algorithm-visualization/composables/useVisualizerTimeline'

const {
  language,
  code,
  input,
  payload,
  generating,
  useExample,
  clearCode,
  clearInput,
  markCustomEditing,
  generate,
  resetAll,
} = useVisualizerState()

const steps = computed(() => payload.value?.steps ?? [])
const playback = useVisualizerPlayback(() => steps.value)

const activeLineLabel = computed(() => {
  if (finished.value) return '运行完毕'
  if (!playback.currentStep.value?.codeLine) return '未开始执行'
  return `当前执行到第 ${playback.currentStep.value.codeLine} 行`
})

useVisualizerTimeline({
  playing: playback.playing,
  speed: playback.speed,
  currentStep: playback.currentStep,
  next: playback.next,
  pause: playback.pause,
})

const currentStep = computed(() => playback.currentStep.value)
const currentStepIndex = computed(() => playback.currentStepIndex.value)
const playing = computed(() => playback.playing.value)
const speed = computed(() => playback.speed.value)
const finished = computed(() => playback.finished.value)

async function handleGenerate() {
  await generate()
  playback.reset()
}

function handleUseExample() {
  useExample()
  playback.reset()
}

function handleClear() {
  clearCode()
  clearInput()
  playback.reset()
}

function handleResetAll() {
  resetAll()
  playback.reset()
}

function play() {
  playback.play()
}

function pause() {
  playback.pause()
}

function next() {
  playback.next()
}

function prev() {
  playback.prev()
}

function resetPlayback() {
  playback.reset()
}

function setSpeed(value: number) {
  playback.setSpeed(value)
}

function seek(value: number) {
  playback.seek(value)
}
</script>

<style scoped>
.algorithm-visualizer-page {
  height: calc(100vh - 64px);
  min-height: 680px;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 18% 16%, rgba(37, 99, 235, 0.06), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #f3f6fb 100%);
  overflow: hidden;
}

.algorithm-visualizer-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(420px, 0.95fr);
  gap: 16px;
  padding: 20px;
}

.visualizer-left {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 12px;
}

.visualizer-right {
  min-width: 0;
  min-height: 0;
}

@media (max-width: 1100px) {
  .algorithm-visualizer-page {
    height: auto;
    min-height: calc(100vh - 64px);
    overflow: visible;
  }

  .algorithm-visualizer-main {
    grid-template-columns: 1fr;
  }

  .visualizer-left {
    grid-template-rows: 520px auto;
  }
}

@media (max-width: 640px) {
  .algorithm-visualizer-main {
    padding: 12px;
  }
}
</style>
