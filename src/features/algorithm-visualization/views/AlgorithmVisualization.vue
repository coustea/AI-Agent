<template>
  <main class="algorithm-visualizer-page">
    <!-- 顶部选择器栏 -->
    <AlgorithmSelectorBar
      v-model:algorithm="algorithm"
      v-model:language="language"
      :algorithms="algorithms"
      :languages="languages"
      :loading="generating"
      :code-ready="!!code.trim()"
      @run="handleRun"
      @reset="resetTemplate"
    />

    <!-- 主内容区 -->
    <section class="algorithm-visualizer-main">
      <!-- 左侧：算法可视化 -->
      <section class="visualizer-left">
        <VisualizerCanvas
          :events="events"
          :current-event="currentEvent"
          :current-step-index="currentStepIndex"
          :visualizer-type="visualizerType"
          :generating="generating"
        />

        <!-- 播放器控制栏 -->
        <VisualizerControlBar
          :events="events"
          :playing="playback.playing.value"
          :current-step-index="currentStepIndex"
          :speed="playback.speed.value"
          :finished="playback.finished.value"
          @play="playback.play"
          @pause="playback.pause"
          @next="playback.next"
          @prev="playback.prev"
          @reset="playback.reset"
          @speed-change="playback.setSpeed"
          @seek="playback.seek"
        />

        <!-- 极简进度条 -->
        <VisualizerProgressBar
          :current="currentStepIndex + 1"
          :total="events.length"
          :message="currentEvent?.message"
        />
      </section>

      <!-- 右侧：代码编辑器 -->
      <aside class="visualizer-right">
        <CodeEditorPanel
          v-model:code="code"
          :language="language"
          :loading="generating"
          :active-line="currentEvent?.line"
          @run="handleRun"
          @reset-template="resetTemplate"
        />
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import VisualizerCanvas from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerCanvas.vue'
import VisualizerProgressBar from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerProgressBar.vue'
import VisualizerControlBar from '@/features/algorithm-visualization/components/algorithm-visualizer/VisualizerControlBar.vue'
import CodeEditorPanel from '@/features/algorithm-visualization/components/algorithm-visualizer/CodeInputPanel.vue'
import AlgorithmSelectorBar from '@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmSelectorBar.vue'
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
  getCurrentVisualizerType,
} = useAlgorithmTemplate()

const {
  events,
  generating,
  run: runAlgorithm,
} = useAlgorithmRun()

const playback = useTracePlayer(() => events.value)
const resolver = useVisualizerResolver(events)

useVisualizerTimeline({
  playing: playback.playing,
  currentEvent: playback.currentEvent,
  speed: playback.speed,
  next: playback.next,
  pause: playback.pause,
})

const currentEvent = computed(() => playback.currentEvent.value)
const currentStepIndex = computed(() => playback.currentStepIndex.value)
const visualizerType = computed(() => resolver.visualizerType.value)

onMounted(() => {
  loadMeta()
})

async function handleRun() {
  await runAlgorithm({
    algorithm: algorithm.value,
    visualizerType: getCurrentVisualizerType(),
    language: language.value,
    code: code.value,
  })
  playback.reset()
  // 运行成功后自动播放
  if (events.value.length > 0) {
    playback.play()
  }
}
</script>

<style scoped>
.algorithm-visualizer-page {
  height: calc(100vh - var(--navbar-height, 72px));
  display: flex;
  flex-direction: column;
  background: #ffffff;
  overflow: hidden;
}

.algorithm-visualizer-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 520px;
  gap: 1px;
  background: var(--color-border);
}

.visualizer-left {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.visualizer-right {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

@media (max-width: 1100px) {
  .algorithm-visualizer-page {
    height: auto;
    overflow: visible;
  }

  .algorithm-visualizer-main {
    grid-template-columns: 1fr;
  }

  .visualizer-left {
    min-height: 500px;
  }
}
</style>
