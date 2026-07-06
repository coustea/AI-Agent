<template>
  <main class="algorithm-visualizer-page">
    <section class="algorithm-visualizer-main">
      <section class="visualizer-left">
        <VisualizerCanvas
          :events="events"
          :current-event="currentEvent"
          :current-step-index="currentStepIndex"
          :visualizer-type="visualizerType"
          :generating="generating"
        />

        <VisualizerControlBar
          :events="events"
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
        <AlgorithmToolbar
          v-model:language="language"
          v-model:algorithm="algorithm"
          :languages="languages"
          :algorithms="algorithms"
          :code="code"
          :generating="generating"
          @run="handleRun"
          @reset-template="resetTemplate"
        />

        <CodeEditorPanel
          v-model:code="code"
          v-model:language="language"
          :loading="generating"
          :active-line="currentEvent?.line"
        />

        <AlgorithmInfoPanel
          :algorithm-name="currentAlgorithmName"
          :difficulty="currentAlgorithmDifficulty"
          :current-event="currentEvent"
          :current-step-index="currentStepIndex"
          :total-steps="events.length"
          :run-error="runError"
        />
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import VisualizerCanvas from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerCanvas.vue'
import VisualizerControlBar from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerControlBar.vue'
import AlgorithmToolbar from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmToolbar.vue'
import CodeEditorPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/CodeInputPanel.vue'
import AlgorithmInfoPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmInfoPanel.vue'
import { useTracePlayer } from '@/features/algorithm-visualization/composables/useTracePlayer'
import { useAlgorithmTemplate } from '@/features/algorithm-visualization/composables/useAlgorithmTemplate'
import { useAlgorithmRun } from '@/features/algorithm-visualization/composables/useAlgorithmRun'
import { useVisualizerResolver } from '@/features/algorithm-visualization/composables/useVisualizerResolver'
import { useVisualizerTimeline } from '@/features/algorithm-visualization/composables/useVisualizerTimeline'

const {
  language,
  algorithm,
  code,
  languages,
  algorithms,
  loadMeta,
  resetTemplate,
  getCurrentAlgorithmInfo,
  getCurrentVisualizerType,
} = useAlgorithmTemplate()

const {
  events,
  runError,
  generating,
  run: runAlgorithm,
} = useAlgorithmRun()

const playback = useTracePlayer(() => events.value)
const resolver = useVisualizerResolver(events)

useVisualizerTimeline({
  playing: playback.playing,
  speed: playback.speed,
  currentEvent: playback.currentEvent,
  next: playback.next,
  pause: playback.pause,
})

const currentEvent = computed(() => playback.currentEvent.value)
const currentStepIndex = computed(() => playback.currentStepIndex.value)
const playing = computed(() => playback.playing.value)
const speed = computed(() => playback.speed.value)
const finished = computed(() => playback.finished.value)
const visualizerType = computed(() => resolver.visualizerType.value)

const currentAlgorithmName = computed(() => getCurrentAlgorithmInfo()?.name ?? '算法可视化')
const currentAlgorithmDifficulty = computed(() => getCurrentAlgorithmInfo()?.difficulty ?? '')

onMounted(() => {
  loadMeta()
})

async function handleRun() {
  await runAlgorithm({
    domain: 'data_structure',
    algorithm: algorithm.value,
    visualizerType: getCurrentVisualizerType(),
    language: language.value,
    code: code.value,
  })
  playback.reset()
}

function play() { playback.play() }
function pause() { playback.pause() }
function next() { playback.next() }
function prev() { playback.prev() }
function resetPlayback() { playback.reset() }
function setSpeed(value: number) { playback.setSpeed(value) }
function seek(value: number) { playback.seek(value) }
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
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 12px;
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
