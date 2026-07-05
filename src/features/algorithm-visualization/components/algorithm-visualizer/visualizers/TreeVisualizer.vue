<template>
  <div class="tree-visualizer">
    <div class="visualizer-meta">
      <div class="visualizer-meta-left">
        <h3>树结构动态可视化</h3>
        <p>自适应树状拓扑布局，支持父子节点边关系绘制及深度/广度遍历动画过程。</p>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
      </div>
    </div>

    <div class="chart-shell">
      <div class="tree-stage">
        <svg class="tree-svg" viewBox="0 0 860 360" preserveAspectRatio="xMidYMid meet">
          <!-- Render Edges -->
          <line
            v-for="edge in treeEdges"
            :key="`${edge.from}-${edge.to}`"
            :x1="edge.fromNode.x"
            :y1="edge.fromNode.y"
            :x2="edge.toNode.x"
            :y2="edge.toNode.y"
            class="tree-link"
            :class="[edge.tone || 'default']"
          />

          <!-- Render Nodes -->
          <g
            v-for="node in nodes"
            :key="node.id"
            :data-node-id="node.id"
            class="tree-node-group"
          >
            <circle
              :cx="node.x"
              :cy="node.y"
              r="24"
              class="tree-node"
              :class="[node.tone || 'default']"
            />
            <text :x="node.x" :y="node.y - 1" class="tree-node-label">{{ node.label || node.id }}</text>
            <text :x="node.x" :y="node.y + 12" class="tree-node-id">{{ node.id }}</text>
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

// Hierarchical DFS tree layout algorithm for auto positioning
const nodes = computed(() => {
  const list = rawNodes.value
  if (list.length === 0) return []

  // Use manual coordinates if any node contains custom positioning
  const hasCoordinates = list.some((n: any) => n.x !== 0 || n.y !== 0)
  if (hasCoordinates) {
    return list
  }

  // Build tree index trees
  const childrenMap = new Map<string, string[]>()
  const parentMap = new Map<string, string>()

  edges.value.forEach((edge: any) => {
    const parent = edge.from
    const child = edge.to
    if (!childrenMap.has(parent)) {
      childrenMap.set(parent, [])
    }
    childrenMap.get(parent)!.push(child)
    parentMap.set(child, parent)
  })

  // Find roots (nodes with no parents)
  const roots = list.filter((n: any) => !parentMap.has(n.id)).map((n: any) => n.id)

  const positions = new Map<string, { x: number; y: number }>()

  // Count children leaves for allocating layout segments
  function countLeaves(nodeId: string): number {
    const children = childrenMap.get(nodeId) || []
    if (children.length === 0) return 1
    return children.reduce((sum, child) => sum + countLeaves(child), 0)
  }

  // Layout tree node recursively
  function layoutNode(nodeId: string, depth: number, leftBound: number, rightBound: number) {
    const children = childrenMap.get(nodeId) || []
    const x = (leftBound + rightBound) / 2
    const y = depth * 80 + 50
    positions.set(nodeId, { x, y })

    if (children.length === 0) return

    let currentLeft = leftBound
    const childLeafCounts = children.map((child) => countLeaves(child))
    const totalChildLeaves = childLeafCounts.reduce((s, c) => s + c, 0)

    children.forEach((child, idx) => {
      const leaves = childLeafCounts[idx] ?? 1
      const fraction = leaves / Math.max(totalChildLeaves, 1)
      const segmentWidth = (rightBound - leftBound) * fraction
      layoutNode(child, depth + 1, currentLeft, currentLeft + segmentWidth)
      currentLeft += segmentWidth
    })
  }

  // Position roots
  let rootLeft = 40
  const widthAvailable = 780
  const rootLeafCounts = roots.map((root) => countLeaves(root))
  const totalRootLeaves = rootLeafCounts.reduce((s, c) => s + c, 0)

  roots.forEach((root, idx) => {
    const leaves = rootLeafCounts[idx] ?? 1
    const fraction = leaves / Math.max(totalRootLeaves, 1)
    const segmentWidth = widthAvailable * fraction
    layoutNode(root, 0, rootLeft, rootLeft + segmentWidth)
    rootLeft += segmentWidth
  })

  // Position any orphan nodes
  list.forEach((node: any) => {
    if (!positions.has(node.id)) {
      positions.set(node.id, { x: 430, y: 50 })
    }
  })

  return list.map((node: any) => {
    const pos = positions.get(node.id) || { x: 430, y: 50 }
    return {
      ...node,
      x: pos.x,
      y: pos.y,
    }
  })
})

const treeEdges = computed(() => {
  return edges.value.map((edge: any) => {
    const fromNode = nodes.value.find((n: any) => n.id === edge.from)
    const toNode = nodes.value.find((n: any) => n.id === edge.to)
    if (!fromNode || !toNode) return null
    return { ...edge, fromNode, toNode }
  }).filter(Boolean)
})

function animateStep() {
  if (!props.currentStep) return

  // Play target nodes animation (scale up / pop effect)
  const targets = props.currentStep.targets || []
  targets.forEach((nodeId) => {
    const el = document.querySelector(`.tree-node-group[data-node-id="${nodeId}"] circle`)
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
.tree-visualizer {
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

.tree-stage {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 360px;
  overflow: hidden;
}

.tree-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  min-height: 360px;
}

.tree-link {
  stroke: #94a3b8;
  stroke-width: 3px;
  stroke-linecap: round;
  transition: stroke 0.3s ease;
}

.tree-link.visited {
  stroke: #10b981;
  stroke-width: 4.5px;
}

.tree-node {
  fill: #ffffff;
  stroke: #cbd5e1;
  stroke-width: 2.5px;
  transition: fill 0.35s ease, stroke 0.35s ease;
}

.tree-node.visited {
  fill: #ecfdf5;
  stroke: #10b981;
}

.tree-node-label {
  font-size: 13px;
  font-weight: 700;
  fill: #0f172a;
  text-anchor: middle;
  pointer-events: none;
}

.tree-node-id {
  font-size: 9px;
  font-weight: 600;
  fill: #94a3b8;
  text-anchor: middle;
  pointer-events: none;
}

.tree-node.visited + .tree-node-label {
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
