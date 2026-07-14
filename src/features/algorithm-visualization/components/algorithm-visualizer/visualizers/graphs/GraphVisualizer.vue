<template>
  <div class="graph-visualizer">
    <div class="chart-shell">
      <div
        v-if="activeNode"
        class="current-status"
      >
        <span class="status-marker"></span>
        当前节点 {{ activeNode.label }}
      </div>

      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>未访问</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
        <span class="legend-item"><i class="legend-dot active"></i>当前</span>
      </div>

      <div v-if="layoutNodes.length" class="graph-container">
        <svg
          class="graph-links-svg"
          viewBox="0 0 1000 600"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <g
            v-for="(edge, idx) in graphEdges"
            :key="idx"
          >
            <line
              :x1="edge.x1"
              :y1="edge.y1"
              :x2="edge.x2"
              :y2="edge.y2"
              :class="['graph-edge', edge.tone || 'default']"
            />
            <text
              v-if="edge.weight !== undefined"
              :x="(edge.x1 + edge.x2) / 2"
              :y="(edge.y1 + edge.y2) / 2 - 5"
              class="graph-edge-weight"
              text-anchor="middle"
            >{{ edge.weight }}</text>
          </g>
        </svg>

        <div
          v-for="node in layoutNodes"
          :key="node.id"
          :class="['graph-node', node.tone || 'default', { active: node.isActive, 'has-distance': node.distance !== undefined }]"
          :data-node-id="node.id"
          :style="{ left: `${node.leftPercent}%`, top: `${node.topPercent}%` }"
        >
          <span class="node-label">{{ node.label }}</span>
          <span v-if="node.distance !== undefined" class="node-distance">距离 {{ node.distance }}</span>
        </div>
      </div>
      <div v-else class="empty-state">等待图数据初始化...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import * as d3 from 'd3'
import type { TraceEvent, VisualEdge, VisualNode } from '@/features/algorithm-visualization/types'

interface GraphConnection {
  u: string
  v: string
  weight?: string | number
}

interface SimulationGraphNode {
  id: string
  sourceNode: VisualNode
  x: number
  y: number
  vx?: number
  vy?: number
  index?: number
}

interface SimulationGraphLink {
  source: string | SimulationGraphNode
  target: string | SimulationGraphNode
  index?: number
}

const props = defineProps<{
  currentEvent: TraceEvent | null
  currentStepIndex: number
  events: TraceEvent[]
}>()

const layoutPositionCache = new Map<string, Map<string, { x: number; y: number }>>()

// 从 trace step 解析图节点
const rawNodes = computed(() => {
  const raw = props.currentEvent?.state?.structure?.nodes
  return Array.isArray(raw) ? raw as VisualNode[] : []
})

const activeNodeIds = computed(() => new Set(
  (props.currentEvent?.targets ?? []).map(target => String(target)),
))

const activeNode = computed(() => rawNodes.value.find(node => activeNodeIds.value.has(String(node.id))) ?? null)

// 构建图的边列表（优先使用节点声明的 edges，否则用默认拓扑）
const edgesList = computed<GraphConnection[]>(() => {
  const nodes = rawNodes.value
  if (nodes.length <= 1) return []

  const connections: GraphConnection[] = []
  const seenConnections = new Set<string>()
  
  let hasExplicitEdges = false
  nodes.forEach(n => {
    if (Array.isArray(n.edges)) {
      hasExplicitEdges = true
      n.edges.forEach((edge: VisualEdge) => {
        if (edge && edge.to !== undefined) {
          const u = String(n.id)
          const v = String(edge.to)
          const key = [u, v].sort().join('::')
          if (!seenConnections.has(key)) {
            connections.push({ u, v, weight: edge.weight })
            seenConnections.add(key)
          }
        }
      })
    }
  })

  if (hasExplicitEdges) {
    return connections
  }

  // 6 节点默认图：标准搜索测试图的环形+交叉边
  if (nodes.length === 6) {
    const defaultEdges: GraphConnection[] = [
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

  // 通用降级：按索引构建环形+交叉边
  for (let i = 0; i < nodes.length; i++) {
    const next = (i + 1) % nodes.length
    connections.push({ u: String(nodes[i]!.id), v: String(nodes[next]!.id) })
    if (i + 2 < nodes.length) {
      connections.push({ u: String(nodes[i]!.id), v: String(nodes[i + 2]!.id) })
    }
  }
  return connections
})

const topologySignature = computed(() => JSON.stringify({
  nodes: rawNodes.value.map(node => String(node.id)),
  edges: edgesList.value.map(edge => [edge.u, edge.v]),
}))

// 用确定性初始位置运行同步力导布局，充分利用画布并减少边交叉。
const layoutNodes = computed(() => {
  const nodes = rawNodes.value
  if (nodes.length === 0) return []

  const signature = topologySignature.value
  const cachedPositions = layoutPositionCache.get(signature)
  if (cachedPositions) {
    return nodes.map(sourceNode => {
      const id = String(sourceNode.id)
      const position = cachedPositions.get(id) ?? { x: 500, y: 300 }
      return {
        ...sourceNode,
        ...position,
        leftPercent: position.x / 10,
        topPercent: position.y / 6,
        isActive: activeNodeIds.value.has(id),
      }
    })
  }

  const simulationNodes: SimulationGraphNode[] = nodes.map((sourceNode, index) => {
    const angle = (index * 2 * Math.PI) / nodes.length - Math.PI / 2
    return {
      id: String(sourceNode.id),
      sourceNode,
      x: 500 + Math.cos(angle) * 270,
      y: 300 + Math.sin(angle) * 190,
    }
  })
  const simulationLinks: SimulationGraphLink[] = edgesList.value.map(edge => ({
    source: edge.u,
    target: edge.v,
  }))

  const simulation = d3.forceSimulation(simulationNodes)
    .force('link', d3.forceLink(simulationLinks)
      .id((node: SimulationGraphNode) => node.id)
      .distance(nodes.length <= 6 ? 225 : 175)
      .strength(0.72))
    .force('charge', d3.forceManyBody().strength(nodes.length <= 8 ? -1250 : -820))
    .force('collide', d3.forceCollide().radius(52).strength(1))
    .force('center', d3.forceCenter(500, 300))
    .force('x', d3.forceX(500).strength(0.025))
    .force('y', d3.forceY(300).strength(0.055))
    .stop()

  for (let tick = 0; tick < 220; tick += 1) simulation.tick()

  const positions = new Map<string, { x: number; y: number }>()
  const resolvedNodes = simulationNodes.map(node => {
    const x = Math.min(920, Math.max(80, node.x ?? 500))
    const y = Math.min(510, Math.max(90, node.y ?? 300))
    positions.set(node.id, { x, y })
    return {
      ...node.sourceNode,
      x,
      y,
      leftPercent: x / 10,
      topPercent: y / 6,
      isActive: activeNodeIds.value.has(node.id),
    }
  })
  layoutPositionCache.set(signature, positions)
  return resolvedNodes
})

// 计算图边的起点/终点 SVG 坐标
const graphEdges = computed(() => {
  const nodes = layoutNodes.value
  const edges = edgesList.value
  const posMap = new Map<string, { x: number; y: number; tone?: string; isActive: boolean }>()
  nodes.forEach(n => posMap.set(String(n.id), { x: n.x, y: n.y, tone: n.tone, isActive: n.isActive }))

  return edges.map(e => {
    const uPos = posMap.get(e.u) || { x: 0, y: 0, tone: 'default', isActive: false }
    const vPos = posMap.get(e.v) || { x: 0, y: 0, tone: 'default', isActive: false }
    
    // 两端节点都已访问时高亮该边（表示遍历路径）
    const isVisitedPath = uPos.tone === 'visited' && vPos.tone === 'visited'

    return {
      x1: uPos.x,
      y1: uPos.y,
      x2: vPos.x,
      y2: vPos.y,
      tone: isVisitedPath && (uPos.isActive || vPos.isActive) ? 'active' : isVisitedPath ? 'visited' : 'default',
      weight: e.weight,
    }
  })
})
</script>

<style scoped>
.graph-visualizer {
  height: 100%;
  min-height: 0;
  display: flex;
  padding: 12px;
  background: transparent;
}

.legend {
  position: absolute;
  top: 12px;
  right: 14px;
  z-index: 1;
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.default {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.legend-dot.visited {
  background: var(--color-success-soft);
  border: 1px solid var(--color-success);
}

.legend-dot.active {
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
}

.current-status {
  position: absolute;
  top: 12px;
  left: 14px;
  z-index: 2;
  min-height: 29px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 9px;
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-strong);
  font-size: 12px;
  font-weight: 700;
}

.status-marker {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
}

.chart-shell {
  position: relative;
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: 12px;
  overflow: hidden;
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
  stroke: var(--color-border-hover);
  stroke-width: 1.5;
  transition: stroke 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  vector-effect: non-scaling-stroke;
}

.graph-edge.visited {
  stroke: var(--color-success);
  stroke-width: 2.5;
}

.graph-edge.active {
  stroke: var(--color-primary);
  stroke-width: 3;
}

.graph-edge-weight {
  fill: var(--color-text-secondary);
  paint-order: stroke;
  stroke: var(--color-bg);
  stroke-width: 5px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
}

.graph-node {
  position: absolute;
  width: 52px;
  min-height: 52px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  padding: 4px;
  background: var(--color-surface);
  border: 1.5px solid var(--color-border-hover);
  font-weight: 750;
  font-size: 13px;
  color: var(--color-text-strong);
  transform: translate(-50%, -50%);
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
  z-index: 1;
}

.graph-node.has-distance {
  width: 62px;
  min-height: 62px;
}

.node-label {
  line-height: 1;
}

.node-distance {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 9px;
  line-height: 1;
}

.graph-node.visited {
  border-color: var(--color-success);
  background: var(--color-success-soft);
  color: var(--color-success);
}

.graph-node.active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-surface);
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--color-primary) 16%, transparent);
}

.graph-node.active .node-distance {
  color: var(--color-surface);
}

.empty-state {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--color-text-faint);
}

@media (prefers-reduced-motion: reduce) {
  .graph-edge,
  .graph-node {
    transition: none;
  }

}
</style>
