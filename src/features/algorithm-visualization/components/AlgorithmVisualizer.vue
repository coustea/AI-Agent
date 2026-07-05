<template>
  <section v-if="trace && currentStep" class="algorithm-visualizer">
    <header class="visualizer-header">
      <div>
        <span class="visualizer-kicker">Algorithm Playback</span>
        <h4>{{ trace.title }}</h4>
        <p>{{ trace.description }}</p>
      </div>
      <span class="visualizer-chip">{{ currentStepIndex + 1 }} / {{ steps.length }}</span>
    </header>

    <div :class="['visualizer-layout', { 'with-code': showCodePanel }]">
      <div class="visualizer-stage">
        <div v-if="currentStep.state.kind === 'array'" class="array-stage">
          <div class="array-bars">
            <TransitionGroup name="algo-bar">
              <div
                v-for="(item, index) in currentStep.state.items"
                :key="item.id"
                :class="['array-bar-card', item.tone || 'default']"
              >
                <div class="array-bar-shell">
                  <div class="array-bar-fill" :style="{ height: `${Math.max(20, Math.abs(item.value) * 12)}px` }"></div>
                </div>
                <strong>{{ item.value }}</strong>
                <div class="pointer-stack">
                  <span
                    v-for="pointer in getPointersForIndex(currentStep.state.pointers || [], index)"
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

        <div v-else-if="currentStep.state.kind === 'tree'" class="tree-stage">
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
              v-for="node in currentStep.state.nodes"
              :key="node.id"
              :class="['tree-node-card', node.tone || 'default']"
              :style="{ left: `${node.x}px`, top: `${node.y}px` }"
            >
              <span class="tree-node-label">{{ node.label }}</span>
            </div>
          </div>
        </div>

        <div v-else-if="currentStep.state.kind === 'graph'" class="graph-stage">
          <svg class="graph-svg" viewBox="0 0 440 280" preserveAspectRatio="xMidYMid meet">
            <line
              v-for="edge in currentStep.state.edges"
              :key="`${edge.from}-${edge.to}`"
              :x1="graphNodeMap[edge.from]?.x || 0"
              :y1="graphNodeMap[edge.from]?.y || 0"
              :x2="graphNodeMap[edge.to]?.x || 0"
              :y2="graphNodeMap[edge.to]?.y || 0"
              :class="['graph-edge', edge.tone || 'default']"
            />
            <g v-for="node in currentStep.state.nodes" :key="node.id">
              <circle :cx="node.x" :cy="node.y" r="26" :class="['graph-node', node.tone || 'default']" />
              <text :x="node.x" :y="node.y + 5" class="graph-label">{{ node.label }}</text>
            </g>
          </svg>
        </div>

        <div v-else-if="currentStep.state.kind === 'dp'" class="dp-stage">
          <div class="dp-grid">
            <div v-if="currentStep.state.headers?.length" class="dp-row header">
              <span v-for="(header, index) in currentStep.state.headers" :key="`h-${index}`" class="dp-cell header">
                {{ header }}
              </span>
            </div>
            <div v-for="(row, rowIndex) in currentStep.state.values" :key="`r-${rowIndex}`" class="dp-row">
              <span
                v-for="(value, colIndex) in row"
                :key="`c-${rowIndex}-${colIndex}`"
                :class="['dp-cell', getDpCellTone(rowIndex, colIndex)]"
              >
                {{ value }}
              </span>
            </div>
          </div>
        </div>

        <div v-else-if="currentStep.state.kind === 'linked-list'" class="linear-stage">
          <div class="linear-strip">
            <div
              v-for="(node, index) in currentStep.state.nodes"
              :key="node.id"
              :class="['linear-node', node.tone || 'default']"
            >
              <span>{{ node.label }}</span>
              <div class="pointer-stack">
                <span
                  v-for="pointer in getLinearPointers(currentStep.state.pointers || [], index)"
                  :key="pointer.label"
                  :class="['pointer-pill', pointer.tone || 'accent']"
                >
                  {{ pointer.label }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="currentStep.state.kind === 'stack-queue'" class="linear-stage">
          <div class="linear-strip" :class="currentStep.state.mode">
            <div
              v-for="(item, index) in currentStep.state.items"
              :key="item.id"
              :class="['linear-node', item.tone || 'default']"
            >
              <span>{{ item.label }}</span>
              <div class="pointer-stack">
                <span
                  v-for="pointer in getLinearPointers(currentStep.state.pointers || [], index)"
                  :key="pointer.label"
                  :class="['pointer-pill', pointer.tone || 'accent']"
                >
                  {{ pointer.label }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <aside v-if="showCodePanel" class="code-panel">
        <div class="code-panel-head">
          <span class="code-kicker">Code</span>
          <span class="code-line-indicator">Line {{ currentStep.activeLine || 1 }}</span>
        </div>
        <div class="code-lines">
          <div
            v-for="(line, index) in trace.codeLines"
            :key="`${index}-${line}`"
            :class="['code-line', { active: index + 1 === (currentStep.activeLine || 1) }]"
          >
            <span class="line-no">{{ index + 1 }}</span>
            <code>{{ line }}</code>
          </div>
        </div>
      </aside>
    </div>



    <div v-if="showPlaybackControls" class="controls">
      <button class="control-btn" :disabled="currentStepIndex === 0" @click="stepBackward">上一步</button>
      <button class="control-btn primary" @click="togglePlay">{{ isPlaying ? '暂停' : '播放' }}</button>
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
      v-if="showPlaybackControls"
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

type TraceTone = 'default' | 'active' | 'swap' | 'sorted' | 'visited' | 'left' | 'right'
type PointerTone = 'accent' | 'success' | 'warning'

interface TracePointer {
  index: number
  label: string
  tone?: PointerTone
}

interface TraceNodePointer {
  nodeIndex?: number
  itemIndex?: number
  label: string
  tone?: PointerTone
}

interface AlgorithmTraceStep {
  caption: string
  message: string
  activeLine?: number
  state:
    | {
        kind: 'array'
        items: Array<{ id: string; value: number; tone?: TraceTone }>
        pointers?: TracePointer[]
      }
    | {
        kind: 'tree'
        nodes: Array<{ id: string; label: string; x: number; y: number; tone?: TraceTone }>
        edges: Array<{ from: string; to: string }>
      }
    | {
        kind: 'graph'
        nodes: Array<{ id: string; label: string; x: number; y: number; tone?: TraceTone }>
        edges: Array<{ from: string; to: string; tone?: TraceTone }>
      }
    | {
        kind: 'dp'
        headers?: string[]
        values: Array<Array<string | number>>
        highlighted?: Array<{ row: number; col: number; tone?: string }>
      }
    | {
        kind: 'linked-list'
        nodes: Array<{ id: string; label: string; tone?: TraceTone }>
        pointers?: TraceNodePointer[]
      }
    | {
        kind: 'stack-queue'
        mode: 'stack' | 'queue'
        items: Array<{ id: string; label: string; tone?: TraceTone }>
        pointers?: TraceNodePointer[]
      }
}

interface AlgorithmTrace {
  title: string
  description: string
  codeLines: string[]
  steps: AlgorithmTraceStep[]
}

const props = withDefaults(defineProps<{
  trace: AlgorithmTrace | null
  showCodePanel?: boolean
  showPlaybackControls?: boolean
  autoPlay?: boolean
}>(), {
  showCodePanel: true,
  showPlaybackControls: true,
  autoPlay: false,
})

const playbackMs = ref(900)
const currentStepIndex = ref(0)
const isPlaying = ref(false)

let playbackTimer: number | null = null

const steps = computed(() => props.trace?.steps || [])
const currentStep = computed<AlgorithmTraceStep | null>(() => steps.value[currentStepIndex.value] ?? steps.value[0] ?? null)

const treeEdges = computed(() => {
  const state = currentStep.value?.state
  if (!state || state.kind !== 'tree') return []
  return state.edges
    .map((edge) => {
      const fromNode = state.nodes.find((node) => node.id === edge.from)
      const toNode = state.nodes.find((node) => node.id === edge.to)
      if (!fromNode || !toNode) return null
      return { ...edge, fromNode, toNode }
    })
    .filter((edge): edge is NonNullable<typeof edge> => Boolean(edge))
})

const graphNodeMap = computed(() => {
  const state = currentStep.value?.state
  if (!state || state.kind !== 'graph') return {}
  return Object.fromEntries(state.nodes.map((node) => [node.id, node]))
})

watch(
  () => props.trace,
  () => {
    stopPlayback()
    currentStepIndex.value = 0
    isPlaying.value = props.autoPlay && steps.value.length > 1
  },
  { deep: true },
)

watch([isPlaying, playbackMs], () => {
  syncPlayback()
})

onUnmounted(() => {
  stopPlayback()
})

function getPointersForIndex(pointers: TracePointer[], index: number) {
  return pointers.filter((pointer) => pointer.index === index)
}

function getLinearPointers(
  pointers: TraceNodePointer[],
  index: number,
) {
  return pointers.filter((pointer) => pointer.nodeIndex === index || pointer.itemIndex === index)
}

function getDpCellTone(row: number, col: number) {
  const state = currentStep.value?.state
  if (!state || state.kind !== 'dp') return ''
  const matched = state.highlighted?.find((item) => item.row === row && item.col === col)
  return matched?.tone || ''
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
  if (currentStepIndex.value >= steps.value.length - 1) currentStepIndex.value = 0
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
  height: 100%;
  min-height: 520px;
  padding: 20px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(248, 250, 255, 0.98), rgba(255, 255, 255, 0.98));
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
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  margin-top: 18px;
}

.visualizer-layout.with-code {
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.9fr);
}

.visualizer-stage,
.code-panel {
  padding: 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(226, 232, 240, 0.9);
  overflow: hidden;
}

.array-stage,
.graph-stage,
.linear-stage {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.array-bars,
.linear-strip {
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 14px;
  min-height: 200px;
}

.linear-strip {
  align-items: center;
  flex-wrap: wrap;
}

.array-bar-card,
.linear-node {
  min-width: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 12px 8px 10px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
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
}

.pointer-stack {
  min-height: 28px;
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
.linear-node.active {
  border-color: rgba(37, 99, 235, 0.45);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.12);
}

.array-bar-card.swap {
  border-color: rgba(245, 158, 11, 0.42);
  background: rgba(255, 251, 235, 0.95);
}

.array-bar-card.sorted,
.linear-node.visited {
  border-color: rgba(16, 185, 129, 0.35);
  background: rgba(236, 253, 245, 0.95);
}

.array-bar-card.left {
  border-color: rgba(37, 99, 235, 0.35);
}

.array-bar-card.right {
  border-color: rgba(249, 115, 22, 0.35);
}

.tree-stage {
  position: relative;
  min-height: 260px;
}

.tree-links,
.graph-svg {
  width: 100%;
  height: 260px;
}

.tree-link,
.graph-edge {
  stroke: rgba(100, 116, 139, 0.75);
  stroke-width: 3;
  stroke-linecap: round;
}

.graph-edge.visited {
  stroke: #2563eb;
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
}

.tree-node-card.active,
.graph-node.active {
  border-color: rgba(37, 99, 235, 0.45);
}

.graph-node {
  fill: rgba(248, 250, 252, 0.96);
  stroke: rgba(226, 232, 240, 0.95);
  stroke-width: 2px;
}

.graph-node.visited,
.graph-node.start {
  fill: rgba(219, 234, 254, 0.95);
  stroke: #2563eb;
}

.graph-label {
  font-size: 14px;
  font-weight: 800;
  fill: #0f172a;
  text-anchor: middle;
}

.dp-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dp-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(48px, 1fr));
  gap: 8px;
}

.dp-cell {
  display: grid;
  place-items: center;
  min-height: 44px;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.95);
  color: #0f172a;
  font-weight: 700;
}

.dp-cell.active {
  border-color: rgba(37, 99, 235, 0.45);
  background: rgba(219, 234, 254, 0.9);
}

.dp-cell.success {
  border-color: rgba(16, 185, 129, 0.35);
  background: rgba(220, 252, 231, 0.92);
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
  .visualizer-layout.with-code {
    grid-template-columns: 1fr;
  }
}
</style>
