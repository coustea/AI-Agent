<template>
  <div class="flowchart-diagram" :class="payload.direction">
    <svg class="edge-layer" :viewBox="`0 0 ${svgWidth} ${svgHeight}`" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <marker id="flowchart-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#475569" />
        </marker>
      </defs>
      <g v-for="edge in layoutEdges" :key="edge.key">
        <path :d="edge.path" fill="none" stroke="#475569" stroke-width="1.5" :marker-end="edge.hasLabel ? undefined : 'url(#flowchart-arrow)'" />
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

.edge-label {
  fill: #475569;
  font-size: 11px;
  font-weight: 600;
  paint-order: stroke;
  stroke: #ffffff;
  stroke-width: 3px;
}

.nodes-layer {
  position: relative;
}

.flow-node {
  position: absolute;
  min-width: 120px;
  max-width: 160px;
  padding: 10px 12px;
  background: #ffffff;
  border: 2px solid #94a3b8;
  border-radius: 8px;
  text-align: center;
  transform: translate(-50%, 0);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}

.flow-node strong {
  display: block;
  font-size: 13px;
  line-height: 1.35;
  color: var(--c-ink, #111827);
}

.flow-node p {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--c-muted, #64748b);
}

.flow-node.start {
  border-color: #2563eb;
  background: #eff6ff;
  border-radius: 999px;
}

.flow-node.end {
  border-color: #16a34a;
  background: #f0fdf4;
  border-radius: 999px;
}

.flow-node.decision {
  border-color: #d97706;
  background: #fffbeb;
  border-radius: 4px;
}

.flow-node.danger {
  border-color: #dc2626;
  background: #fef2f2;
}
</style>
