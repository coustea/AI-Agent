<template>
  <div class="graph-visualizer">
    <div class="visualizer-meta">
      <div class="visualizer-meta-left">
        <h3>图遍历动态可视化</h3>
        <p>支持自适应图节点、有权/无权边绘制，以及深度优先 (DFS)/广度优先 (BFS) 遍历过程高亮。</p>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
      </div>
    </div>

    <div class="chart-shell">
      <div class="graph-stage">
        <!-- SVG lines for edges -->
        <svg class="graph-svg" viewBox="0 0 860 360" preserveAspectRatio="xMidYMid meet">
          <!-- Render Edges -->
          <g v-for="edge in edges" :key="`${edge.from}-${edge.to}`">
            <line
              :x1="nodeMap[edge.from]?.x || 0"
              :y1="nodeMap[edge.from]?.y || 0"
              :x2="nodeMap[edge.to]?.x || 0"
              :y2="nodeMap[edge.to]?.y || 0"
              class="graph-edge"
              :class="[edge.tone || 'default']"
              :data-edge-id="`${edge.from}-${edge.to}`"
            />
            <!-- Edge Weight Text -->
            <text
              v-if="edge.weight !== undefined"
              :x="((nodeMap[edge.from]?.x || 0) + (nodeMap[edge.to]?.x || 0)) / 2"
              :y="((nodeMap[edge.from]?.y || 0) + (nodeMap[edge.to]?.y || 0)) / 2 - 8"
              class="edge-weight"
            >
              {{ edge.weight }}
            </text>
          </g>
          <!-- Render Nodes -->
          <g
            v-for="node in nodes"
            :key="node.id"
            :data-node-id="node.id"
            class="graph-node-group"
          >
            <circle
              :cx="node.x"
              :cy="node.y"
              r="24"
              class="graph-node"
              :class="[node.tone || 'default']"
            />
            <text :x="node.x" :y="node.y + 5" class="graph-label">{{ node.label || node.id }}</text>
          </g>
        </svg>

        <div v-if="!nodes.length" class="empty-state">
          等待初始化节点数据...
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import gsap from 'gsap'
import type { VisualStep } from '@/features/algorithm-visualization/types'

interface Props {
  initialState: any
  currentStep: VisualStep | null
  currentStepIndex: number
}

const props = defineProps<Props>()

const rawNodes = computed<any[]>(() => (props.currentStep?.payload?.nodes as any[]) || [])
const edges = computed<any[]>(() => (props.currentStep?.payload?.edges as any[]) || [])

const nodes = computed(() => {
  const list = rawNodes.value
  if (list.length === 0) return []

  const hasCoordinates = list.some((n: any) => n.x !== 0 || n.y !== 0)
  if (hasCoordinates) {
    return list
  }

  const count = list.length
  const centerX = 430
  const centerY = 180
  const radius = Math.min(centerX, centerY) - 40

  return list.map((node: any, index: number) => {
    const angle = (2 * Math.PI * index) / Math.max(count, 1)
    const x = centerX + radius * Math.cos(angle)
    const y = centerY + radius * Math.sin(angle)
    return {
      ...node,
      x,
      y,
    }
  })
})

const nodeMap = computed(() => Object.fromEntries(nodes.value.map((n: any) => [n.id, n])))

function animateStep() {
  if (!props.currentStep) return

  // Scale target nodes
  const targets = props.currentStep.targets || []
  targets.forEach((nodeId) => {
    const el = document.querySelector(`.graph-node-group[data-node-id="${nodeId}"] circle`)
    if (el) {
      gsap.fromTo(
        el,
        { scale: 1 },
        {
          scale: 1.2,
          duration: 0.25,
          yoyo: true,
          repeat: 1,
          ease: 'power2.out',
          transformOrigin: 'center center',
        }
      )
    }
  })
}

watch(
  () => props.currentStepIndex,
  async () => {
    await nextTick()
    animateStep()
  },
  { immediate: true }
)
</script>

<style scoped>
.graph-visualizer {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
  padding: 18px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95));
}

.visualizer-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.visualizer-meta h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 760;
  color: #0f172a;
}

.visualizer-meta p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
}

.legend {
  display: flex;
  gap: 12px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #475569;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot.default {
  background: #cbd5e1;
  border: 1px solid #94a3b8;
}

.legend-dot.visited {
  background: rgba(220, 252, 231, 0.95);
  border: 1px solid #10b981;
}

.chart-shell {
  min-height: 0;
  border-radius: 24px;
  background: rgba(241, 245, 249, 0.62);
  border: 1px solid rgba(226, 232, 240, 0.96);
  padding: 16px;
  position: relative;
}

.graph-stage {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 360px;
  overflow: hidden;
}

.graph-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  min-height: 360px;
}

.graph-edge {
  stroke: #94a3b8;
  stroke-width: 3px;
  stroke-linecap: round;
  transition: stroke 0.3s ease;
}

.graph-edge.visited {
  stroke: #10b981;
  stroke-width: 4.5px;
}

.edge-weight {
  font-size: 11px;
  font-weight: 700;
  fill: #475569;
  text-anchor: middle;
}

.graph-node {
  fill: #ffffff;
  stroke: #cbd5e1;
  stroke-width: 2.5px;
  transition: fill 0.35s ease, stroke 0.35s ease;
}

.graph-node.visited {
  fill: #ecfdf5;
  stroke: #10b981;
}

.graph-label {
  font-size: 13px;
  font-weight: 700;
  fill: #0f172a;
  text-anchor: middle;
  pointer-events: none;
}

.graph-node.visited + .graph-label {
  fill: #065f46;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #94a3b8;
}
</style>
