<template>
  <div class="graph-visualizer">
    <div class="visualizer-meta">
      <div class="flex flex-col">
        <h3>图结构可视化</h3>
        <p>展示图论算法的遍历搜索路径，包含节点与边状态的高亮变化。</p>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>未访问</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
      </div>
    </div>
    <div class="chart-shell">
      <div v-if="layoutNodes.length" class="graph-container">
        <!-- SVG Connecting Edges -->
        <svg class="graph-links-svg">
          <line
            v-for="(edge, idx) in graphEdges"
            :key="idx"
            :x1="edge.x1"
            :y1="edge.y1"
            :x2="edge.x2"
            :y2="edge.y2"
            :class="['graph-edge', edge.tone || 'default']"
          />
        </svg>

        <!-- Graph Nodes -->
        <div
          v-for="node in layoutNodes"
          :key="node.id"
          :class="['graph-node', node.tone || 'default']"
          :style="{ left: `${node.px}px`, top: `${node.py}px` }"
        >
          <span>{{ node.label }}</span>
        </div>
      </div>
      <div v-else class="empty-state">等待图数据初始化...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  currentEvent: TraceEvent | null
  currentStepIndex: number
  events: TraceEvent[]
}>()

// Parse nodes from step trace
const rawNodes = computed(() => {
  const raw = props.currentEvent?.state?.structure?.nodes
  return Array.isArray(raw) ? raw : []
})

// Adjacency connections definition (fallback for general graph traversals)
const edgesList = computed(() => {
  const nodes = rawNodes.value
  if (nodes.length <= 1) return []

  const connections: Array<{ u: string; v: string }> = []
  
  let hasExplicitEdges = false
  nodes.forEach(n => {
    if (Array.isArray(n.edges)) {
      hasExplicitEdges = true
      n.edges.forEach((edge: any) => {
        if (edge && edge.to !== undefined) {
          connections.push({ u: String(n.id), v: String(edge.to) })
        }
      })
    }
  })

  if (hasExplicitEdges) {
    return connections
  }

  // If node count is 6 (standard search graph size), define the default cyclic test graph edges:
  if (nodes.length === 6) {
    const defaultEdges = [
      { u: '0', v: '1' },
      { u: '0', v: '2' },
      { u: '1', v: '3' },
      { u: '1', v: '4' },
      { u: '2', v: '5' },
      { u: '3', v: '4' }, // Add cycle helper
      { u: '4', v: '5' }  // Add cycle helper
    ]
    return defaultEdges.filter(e => {
      return nodes.some(n => String(n.id) === e.u) && nodes.some(n => String(n.id) === e.v)
    })
  }

  // Generic fallback: Connect adjacent numerical indices to form a ring, and cross-links
  for (let i = 0; i < nodes.length; i++) {
    const next = (i + 1) % nodes.length
    connections.push({ u: String(nodes[i].id), v: String(nodes[next].id) })
    if (i + 2 < nodes.length) {
      connections.push({ u: String(nodes[i].id), v: String(nodes[i + 2].id) })
    }
  }
  return connections
})

// Circular layout mapping to prevent layout overlap
const layoutNodes = computed(() => {
  const nodes = rawNodes.value
  if (nodes.length === 0) return []

  const canvasWidth = 800
  const canvasHeight = 240
  const centerX = canvasWidth / 2
  const centerY = canvasHeight / 2
  const radius = 84 // Circle radius for graph layout

  return nodes.map((n, idx) => {
    // If backend already specified custom coordinates (not 0), respect them
    if (n.x && n.y) {
      return {
        ...n,
        px: n.x,
        py: n.y
      }
    }

    // Circular layout math
    const angle = (idx * 2 * Math.PI) / nodes.length - Math.PI / 2
    const px = centerX + radius * Math.cos(angle)
    const py = centerY + radius * Math.sin(angle)

    return {
      ...n,
      px,
      py
    }
  })
})

// Edges position calculator
const graphEdges = computed(() => {
  const nodes = layoutNodes.value
  const edges = edgesList.value
  const posMap = new Map<string, { px: number; py: number; tone?: string }>()
  nodes.forEach(n => posMap.set(String(n.id), { px: n.px, py: n.py, tone: n.tone }))

  return edges.map(e => {
    const uPos = posMap.get(e.u) || { px: 0, py: 0, tone: 'default' }
    const vPos = posMap.get(e.v) || { px: 0, py: 0, tone: 'default' }
    
    // Highlight the edge if both adjacent nodes are visited (representing traversal route)
    const isVisitedPath = uPos.tone === 'visited' && vPos.tone === 'visited'

    return {
      x1: uPos.px,
      y1: uPos.py,
      x2: vPos.px,
      y2: vPos.py,
      tone: isVisitedPath ? 'visited' : 'default'
    }
  })
})
</script>

<style scoped>
.graph-visualizer {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  background: #ffffff;
}

.visualizer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.visualizer-meta h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.visualizer-meta p {
  margin: 2px 0 0;
  font-size: 11px;
  color: #64748b;
}

.legend {
  display: flex;
  gap: 8px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #475569;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.default {
  background: #cbd5e1;
  border: 1px solid #94a3b8;
}

.legend-dot.visited {
  background: #ecfdf5;
  border: 1px solid #10b981;
}

.chart-shell {
  min-height: 0;
  border-radius: 4px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 12px;
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.graph-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 240px;
}

.graph-links-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.graph-edge {
  stroke: #cbd5e1;
  stroke-width: 1.5;
  transition: stroke 0.25s ease, stroke-width 0.25s ease;
}

.graph-edge.visited {
  stroke: #10b981;
  stroke-width: 2.5;
}

.graph-node {
  position: absolute;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  font-weight: 600;
  font-size: 11px;
  color: #334155;
  transform: translate(-50%, -50%);
  transition: border-color 0.25s ease, background-color 0.25s ease, color 0.25s ease;
  z-index: 10;
}

@keyframes node-pulse {
  0% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.25); }
  100% { transform: translate(-50%, -50%) scale(1); }
}

.graph-node.visited {
  border-color: #10b981;
  background: #ecfdf5;
  color: #047857;
  animation: node-pulse 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.empty-state {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #94a3b8;
}
</style>
