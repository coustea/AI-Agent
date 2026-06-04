<template>
  <div class="flowchart-diagram" :class="payload.direction">
    <svg class="edge-layer" :viewBox="`0 0 ${svgWidth} ${svgHeight}`" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <marker id="flowchart-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#475569" />
        </marker>
      </defs>
      <g v-for="edge in layoutEdges" :key="edge.key">
        <path :d="edge.path" class="flow-edge" fill="none" :marker-end="edge.hasLabel ? undefined : 'url(#flowchart-arrow)'" />
        <text v-if="edge.label" :x="edge.labelX" :y="edge.labelY" text-anchor="middle" class="edge-label">{{ edge.label }}</text>
      </g>
    </svg>
    <div class="nodes-layer">
      <div
        v-for="node in layoutNodes"
        :key="node.id"
        class="flow-node"
        :class="[node.type]"
        :style="{ left: `${node.x}px`, top: `${node.y}px` }"
      >
        <strong>{{ node.title }}</strong>
        <p v-if="node.short_desc">{{ node.short_desc }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { FlowchartPayload } from '@/chat/types/chat'

const props = defineProps<{
  payload: FlowchartPayload
}>()

const NODE_W = 140
const NODE_H = 56
const GAP_X = 180
const GAP_Y = 90

const layoutNodes = computed(() => {
  const nodes = props.payload.nodes
  const isVertical = props.payload.direction === 'vertical'
  return nodes.map((node, i) => ({
    ...node,
    x: isVertical ? 0 : i * GAP_X,
    y: isVertical ? i * GAP_Y : 0,
  }))
})

const nodeMap = computed(() => {
  const map = new Map<string, { x: number; y: number }>()
  layoutNodes.value.forEach((n) => map.set(n.id, { x: n.x, y: n.y }))
  return map
})

const svgWidth = computed(() => {
  const xs = layoutNodes.value.map((n) => n.x + NODE_W)
  return Math.max(200, ...xs) + 20
})

const svgHeight = computed(() => {
  const ys = layoutNodes.value.map((n) => n.y + NODE_H)
  return Math.max(100, ...ys) + 20
})

const layoutEdges = computed(() => {
  return props.payload.edges.map((edge, i) => {
    const src = nodeMap.value.get(edge.from)
    const tgt = nodeMap.value.get(edge.to)
    if (!src || !tgt) return { key: `e-${i}`, path: '', label: edge.label, labelX: 0, labelY: 0, hasLabel: !!edge.label }

    const isVertical = props.payload.direction === 'vertical'
    let path: string
    let labelX: number
    let labelY: number

    if (isVertical) {
      const sx = src.x + NODE_W / 2
      const sy = src.y + NODE_H
      const tx = tgt.x + NODE_W / 2
      const ty = tgt.y
      const midY = (sy + ty) / 2
      path = `M${sx},${sy} C${sx},${midY} ${tx},${midY} ${tx},${ty}`
      labelX = (sx + tx) / 2 + 8
      labelY = midY
    } else {
      const sx = src.x + NODE_W
      const sy = src.y + NODE_H / 2
      const tx = tgt.x
      const ty = tgt.y + NODE_H / 2
      const midX = (sx + tx) / 2
      path = `M${sx},${sy} C${midX},${sy} ${midX},${ty} ${tx},${ty}`
      labelX = midX
      labelY = (sy + ty) / 2 - 6
    }

    return { key: `e-${i}`, path, label: edge.label, labelX, labelY, hasLabel: !!edge.label }
  })
})
</script>

<style scoped>
.flowchart-diagram {
  position: relative;
  min-height: 200px;
  overflow: auto;
}

.edge-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.flow-edge {
  stroke: #94a3b8;
  stroke-width: 2px;
  stroke-dasharray: 6 4;
  animation: flow-dash 30s linear infinite;
}

@keyframes flow-dash {
  to { stroke-dashoffset: -1000; }
}

.edge-label {
  fill: #334155;
  font-size: 11px;
  font-weight: 700;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 4px;
}

.nodes-layer {
  position: relative;
}

.flow-node {
  position: absolute;
  min-width: 130px;
  max-width: 160px;
  padding: 12px 14px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  text-align: center;
  transform: translate(-50%, 0);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
  z-index: 2;
}

.flow-node:hover {
  transform: translate(-50%, -4px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
}

.flow-node strong {
  display: block;
  font-size: 13px;
  line-height: 1.4;
  color: var(--c-ink, #0f172a);
  overflow-wrap: break-words;
  word-break: break-all;
}

.flow-node p {
  margin: 6px 0 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--c-muted, #64748b);
  overflow-wrap: break-words;
  word-break: break-all;
}

.flow-node.start {
  border: 2px solid #3b82f6;
  background: #eff6ff;
  border-radius: 999px;
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.15);
}

.flow-node.end {
  border: 2px solid #10b981;
  background: #ecfdf5;
  border-radius: 999px;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.15);
}

.flow-node.decision {
  border: 2px solid #f59e0b;
  background: #fefce8;
  border-radius: 8px;
  transform: translate(-50%, 0) rotate(2deg);
}

.flow-node.decision:hover {
  transform: translate(-50%, -4px) rotate(0deg);
}

.flow-node.danger {
  border: 2px solid #ef4444;
  background: #fef2f2;
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.15);
}
</style>
