<template>
  <section v-if="plan && currentStep" class="algorithm-visualizer">
    <header class="visualizer-header">
      <div>
        <span class="visualizer-kicker">Algorithm Playback</span>
        <h4>{{ plan.title }}</h4>
        <p>{{ plan.description }}</p>
      </div>
      <span class="visualizer-chip">{{ currentStepIndex + 1 }} / {{ steps.length }}</span>
    </header>

    <div class="visualizer-layout">
      <div class="visualizer-stage">
        <div v-if="arrayStep" class="array-stage">
          <div class="array-bars">
            <TransitionGroup name="algo-bar">
              <div
                v-for="(item, index) in arrayStep.items"
                :key="item.id"
                :class="['array-bar-card', item.tone || 'default']"
              >
                <div class="array-bar-shell">
                  <div
                    class="array-bar-fill"
                    :style="{ height: `${Math.max(20, Math.abs(item.value) * 12)}px` }"
                  ></div>
                </div>
                <strong>{{ item.value }}</strong>
                <div class="pointer-stack">
                  <span
                    v-for="pointer in getPointersForIndex(arrayStep.pointers || [], index)"
                    :key="pointer.label"
                    :class="['pointer-pill', pointer.tone || 'accent']"
                  >
                    {{ pointer.label }}
                  </span>
                </div>
              </div>
            </TransitionGroup>
          </div>
        </div>

        <div v-else-if="treeStep" class="tree-stage">
          <svg class="tree-links" viewBox="0 0 440 260" preserveAspectRatio="xMidYMid meet">
            <line
              v-for="edge in treeEdges"
              :key="`${edge.from}-${edge.to}`"
              :x1="edge.fromNode.x"
              :y1="edge.fromNode.y"
              :x2="edge.toNode.x"
              :y2="edge.toNode.y"
              class="tree-link"
            />
          </svg>

          <div class="tree-node-layer">
            <div
              v-for="node in treeStep.nodes"
              :key="node.id"
              :class="['tree-node-card', node.tone || 'default']"
              :style="{ left: `${node.x}px`, top: `${node.y}px` }"
            >
              <span class="tree-node-label">{{ node.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <aside class="code-panel">
        <div class="code-panel-head">
          <span class="code-kicker">Code</span>
          <span class="code-line-indicator">Line {{ currentActiveLine }}</span>
        </div>
        <div class="code-lines">
          <div
            v-for="(line, index) in plan.codeLines"
            :key="`${index}-${line}`"
            :class="['code-line', { active: index + 1 === currentActiveLine }]"
          >
            <span class="line-no">{{ index + 1 }}</span>
            <code>{{ line }}</code>
          </div>
        </div>
      </aside>
    </div>

    <transition name="message-fade" mode="out-in">
      <div :key="currentStepIndex" class="step-message">
        <span class="step-caption">{{ currentCaption }}</span>
        <p>{{ currentMessage }}</p>
      </div>
    </transition>

    <div class="controls">
      <button class="control-btn" :disabled="currentStepIndex === 0" @click="stepBackward">上一步</button>
      <button class="control-btn primary" @click="togglePlay">
        {{ isPlaying ? '暂停' : '播放' }}
      </button>
      <button class="control-btn" :disabled="currentStepIndex >= steps.length - 1" @click="stepForward">下一步</button>
      <button class="control-btn ghost" @click="resetPlayback">重置</button>
      <label class="speed-select">
        <span>速度</span>
        <select v-model.number="playbackMs">
          <option :value="1200">慢</option>
          <option :value="900">中</option>
          <option :value="650">快</option>
        </select>
      </label>
    </div>

    <input
      v-model.number="currentStepIndex"
      class="timeline"
      type="range"
      min="0"
      :max="Math.max(0, steps.length - 1)"
      step="1"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import {
  type ArraySnapshot,
  getAlgorithmVisualizationPlan,
  type AlgorithmQuestionLike,
  type PointerMark,
  type TreeSnapshot,
} from '@/features/question-bank/utils/algorithmVisualization'

const props = defineProps<{
  question: AlgorithmQuestionLike
}>()

const playbackMs = ref(900)
const currentStepIndex = ref(0)
const isPlaying = ref(false)

let playbackTimer: number | null = null

const plan = computed(() => getAlgorithmVisualizationPlan(props.question))
const steps = computed(() => plan.value?.steps || [])
const currentStep = computed(() => steps.value[currentStepIndex.value] ?? steps.value[0] ?? null)
const arrayStep = computed<ArraySnapshot | null>(() => {
  const step = currentStep.value
  return step?.kind === 'array' ? step : null
})
const treeStep = computed<TreeSnapshot | null>(() => {
  const step = currentStep.value
  return step?.kind === 'tree' ? step : null
})
const currentActiveLine = computed(() => currentStep.value?.activeLine ?? 1)
const currentCaption = computed(() => currentStep.value?.caption ?? '')
const currentMessage = computed(() => currentStep.value?.message ?? '')

const treeEdges = computed(() => {
  const step = treeStep.value
  if (!step) return []

  return step.edges
    .map((edge) => {
      const fromNode = step.nodes.find((node) => node.id === edge.from)
      const toNode = step.nodes.find((node) => node.id === edge.to)
      if (!fromNode || !toNode) return null
      return { ...edge, fromNode, toNode }
    })
    .filter((edge): edge is NonNullable<typeof edge> => Boolean(edge))
})

watch(
  steps,
  () => {
    stopPlayback()
    currentStepIndex.value = 0
    isPlaying.value = false
  },
  { deep: true },
)

watch([isPlaying, playbackMs], () => {
  syncPlayback()
})

onUnmounted(() => {
  stopPlayback()
})

function getPointersForIndex(pointers: PointerMark[], index: number): PointerMark[] {
  return pointers.filter(pointer => pointer.index === index)
}

function syncPlayback() {
  stopPlayback()

  if (!isPlaying.value || steps.value.length <= 1) return

  playbackTimer = window.setInterval(() => {
    if (currentStepIndex.value >= steps.value.length - 1) {
      isPlaying.value = false
      stopPlayback()
      return
    }
    currentStepIndex.value += 1
  }, playbackMs.value)
}

function stopPlayback() {
  if (playbackTimer !== null) {
    window.clearInterval(playbackTimer)
    playbackTimer = null
  }
}

function togglePlay() {
  if (!steps.value.length) return
  if (currentStepIndex.value >= steps.value.length - 1) {
    currentStepIndex.value = 0
  }
  isPlaying.value = !isPlaying.value
}

function stepForward() {
  stopPlayback()
  isPlaying.value = false
  currentStepIndex.value = Math.min(currentStepIndex.value + 1, steps.value.length - 1)
}

function stepBackward() {
  stopPlayback()
  isPlaying.value = false
  currentStepIndex.value = Math.max(currentStepIndex.value - 1, 0)
}

function resetPlayback() {
  stopPlayback()
  isPlaying.value = false
  currentStepIndex.value = 0
}
</script>

<style scoped>
.algorithm-visualizer {
  margin-top: 18px;
  padding: 20px;
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(248, 250, 255, 0.96), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(191, 219, 254, 0.75);
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.08);
}

.visualizer-header,
.controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.visualizer-kicker,
.code-kicker {
  display: inline-block;
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.visualizer-header h4 {
  margin: 6px 0 4px;
  color: #0f172a;
  font-size: 1.05rem;
  font-weight: 800;
}

.visualizer-header p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
}

.visualizer-chip,
.code-line-indicator {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(219, 234, 254, 0.85);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 800;
  flex-shrink: 0;
}

.visualizer-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(260px, 0.9fr);
  gap: 16px;
  margin-top: 18px;
}

.visualizer-stage,
.code-panel {
  padding: 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(226, 232, 240, 0.9);
  overflow: hidden;
}

.array-stage {
  min-height: 240px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.array-bars {
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 14px;
  min-height: 200px;
}

.array-bar-card {
  width: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 12px 8px 10px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  transition: background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

.array-bar-shell {
  width: 100%;
  min-height: 130px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.array-bar-fill {
  width: 44px;
  border-radius: 14px 14px 10px 10px;
  background: linear-gradient(180deg, #60a5fa, #2563eb);
  transition: height 0.55s cubic-bezier(0.25, 1, 0.5, 1), background 0.3s ease;
}

.array-bar-card strong {
  color: #0f172a;
  font-size: 15px;
}

.pointer-stack {
  min-height: 38px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}

.pointer-pill {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.pointer-pill.accent {
  background: rgba(219, 234, 254, 0.9);
  color: #2563eb;
}

.pointer-pill.warning {
  background: rgba(254, 243, 199, 0.92);
  color: #d97706;
}

.pointer-pill.success {
  background: rgba(220, 252, 231, 0.92);
  color: #059669;
}

.array-bar-card.active,
.tree-node-card.active {
  border-color: rgba(37, 99, 235, 0.45);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.12);
}

.array-bar-card.swap,
.tree-node-card.pivot {
  border-color: rgba(245, 158, 11, 0.42);
  background: rgba(255, 251, 235, 0.95);
}

.array-bar-card.swap .array-bar-fill {
  background: linear-gradient(180deg, #fbbf24, #f59e0b);
}

.array-bar-card.sorted,
.tree-node-card.sorted {
  border-color: rgba(16, 185, 129, 0.35);
  background: rgba(236, 253, 245, 0.95);
}

.array-bar-card.sorted .array-bar-fill {
  background: linear-gradient(180deg, #34d399, #10b981);
}

.array-bar-card.left .array-bar-fill {
  background: linear-gradient(180deg, #60a5fa, #2563eb);
}

.array-bar-card.right .array-bar-fill {
  background: linear-gradient(180deg, #fbbf24, #ea580c);
}

.algo-bar-move {
  transition: transform 0.55s cubic-bezier(0.25, 1, 0.5, 1);
}

.tree-stage {
  position: relative;
  min-height: 240px;
}

.tree-links {
  width: 100%;
  height: 240px;
}

.tree-link {
  stroke: rgba(100, 116, 139, 0.75);
  stroke-width: 3;
  stroke-linecap: round;
  transition: all 0.55s cubic-bezier(0.25, 1, 0.5, 1);
}

.tree-node-layer {
  position: absolute;
  inset: 0;
}

.tree-node-card {
  position: absolute;
  width: 56px;
  height: 56px;
  margin-left: -28px;
  margin-top: -28px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.95);
  color: #0f172a;
  font-size: 16px;
  font-weight: 800;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
  transition: left 0.55s cubic-bezier(0.25, 1, 0.5, 1), top 0.55s cubic-bezier(0.25, 1, 0.5, 1), background-color 0.3s ease, border-color 0.3s ease;
}

.tree-node-card.pivot {
  background: rgba(255, 251, 235, 0.96);
  color: #b45309;
}

.code-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.code-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.code-lines {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.code-line {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.code-line.active {
  background: rgba(219, 234, 254, 0.72);
  border-color: rgba(96, 165, 250, 0.55);
}

.line-no {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
  text-align: right;
}

.code-line code {
  color: #0f172a;
  font-size: 12.5px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.step-message {
  margin-top: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(239, 246, 255, 0.75);
  border: 1px solid rgba(191, 219, 254, 0.8);
}

.step-caption {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
}

.step-message p {
  margin: 10px 0 0;
  color: #334155;
  font-size: 13.5px;
  line-height: 1.65;
}

.controls {
  margin-top: 16px;
  flex-wrap: wrap;
  justify-content: flex-start;
}

.control-btn {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  background: rgba(255, 255, 255, 0.9);
  color: #334155;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.control-btn:hover:not(:disabled) {
  border-color: rgba(37, 99, 235, 0.3);
  color: #2563eb;
}

.control-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.control-btn.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.control-btn.primary:hover:not(:disabled) {
  color: #fff;
  background: #1d4ed8;
}

.control-btn.ghost {
  background: transparent;
}

.speed-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(203, 213, 225, 0.9);
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.speed-select select {
  border: none;
  background: transparent;
  color: #0f172a;
  font-weight: 700;
  outline: none;
}

.timeline {
  width: 100%;
  margin-top: 14px;
  accent-color: #2563eb;
}

.message-fade-enter-active,
.message-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.message-fade-enter-from,
.message-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (max-width: 980px) {
  .visualizer-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .algorithm-visualizer,
  .visualizer-stage,
  .code-panel {
    padding: 16px;
  }

  .array-bars {
    gap: 10px;
  }

  .array-bar-card {
    width: 58px;
    padding: 10px 6px;
  }

  .array-bar-fill {
    width: 36px;
  }
}
</style>
