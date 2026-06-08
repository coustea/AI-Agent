<template>
  <div class="flowchart-diagram" :class="payload.direction">
    <!-- Decorative Grid Background -->
    <div class="flow-bg-grid"></div>

    <svg class="edge-layer" :viewBox="`0 0 ${svgWidth} ${svgHeight}`" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <marker id="flow-arrow-blue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto-start-reverse">
          <path d="M0,1 L8,5 L0,9 Z" fill="#3b82f6" />
        </marker>
        <marker id="flow-arrow-gray" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto-start-reverse">
          <path d="M0,1 L8,5 L0,9 Z" fill="#94a3b8" />
        </marker>
        <linearGradient id="edge-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#3b82f6" />
          <stop offset="100%" stop-color="#8b5cf6" />
        </linearGradient>
      </defs>
      
      <g v-for="edge in layoutEdges" :key="edge.key">
        <path 
          :d="edge.path" 
          class="flow-edge" 
          :class="{ 'animated': !edge.hasLabel }"
          fill="none" 
          :stroke="edge.hasLabel ? '#94a3b8' : 'url(#edge-grad)'"
          :marker-end="edge.hasLabel ? 'url(#flow-arrow-gray)' : 'url(#flow-arrow-blue)'" 
        />
        <g v-if="edge.label" class="edge-label-group">
          <rect 
            :x="edge.labelX - (edge.label.length * 5) - 6" 
            :y="edge.labelY - 10" 
            :width="(edge.label.length * 10) + 12" 
            height="20" 
            rx="10" 
            fill="white" 
            stroke="#e2e8f0" 
          />
          <text :x="edge.labelX" :y="edge.labelY + 4" text-anchor="middle" class="edge-label">{{ edge.label }}</text>
        </g>
      </g>
    </svg>
    
    <div class="nodes-layer">
      <div
        v-for="(node, index) in layoutNodes"
        :key="node.id"
        class="flow-node"
        :class="[node.type]"
        :style="{ left: `${node.x}px`, top: `${node.y}px` }"
      >
        <div class="node-index" v-if="node.type !== 'decision'">{{ index + 1 }}</div>
        <div class="node-content">
          <strong>{{ node.title }}</strong>
          <p v-if="node.short_desc">{{ node.short_desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FlowchartPayload } from '@/features/chat/model/chat'

const props = defineProps<{
  payload: FlowchartPayload
}>()

const NODE_W = 160
const NODE_H = 64
const GAP_X = 200
const GAP_Y = 110

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
  return Math.max(200, ...xs) + 40
})

const svgHeight = computed(() => {
  const ys = layoutNodes.value.map((n) => n.y + NODE_H)
  return Math.max(100, ...ys) + 40
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
      labelX = (sx + tx) / 2
      labelY = midY
    } else {
      const sx = src.x + NODE_W
      const sy = src.y + NODE_H / 2
      const tx = tgt.x
      const ty = tgt.y + NODE_H / 2
      const midX = (sx + tx) / 2
      path = `M${sx},${sy} C${midX},${sy} ${midX},${ty} ${tx},${ty}`
      labelX = midX
      labelY = sy
    }

    return { key: `e-${i}`, path, label: edge.label, labelX, labelY, hasLabel: !!edge.label }
  })
})
</script>

<style scoped>
.flowchart-diagram {
  position: relative;
  min-height: 250px;
  overflow: auto;
  padding: 20px;
  background: linear-gradient(135deg, var(--color-bg) 0%, var(--color-surface-hover) 100%);
  border-radius: 16px;
  box-shadow: inset 0 2px 10px rgba(0,0,0,0.02);
}

.flow-bg-grid {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-size: 20px 20px;
  background-image: radial-gradient(circle, var(--color-border-hover) 1px, transparent 1px);
  opacity: 0.5;
  pointer-events: none;
  border-radius: 16px;
}

.edge-layer {
  position: absolute;
  top: 20px;
  left: 20px;
  pointer-events: none;
  z-index: 1;
}

.flow-edge {
  stroke-width: 3px;
  stroke-linecap: round;
  transition: all 0.3s ease;
}

.flow-edge.animated {
  stroke-dasharray: 8 6;
  animation: flow-dash 15s linear infinite;
}

@keyframes flow-dash {
  to { stroke-dashoffset: -200; }
}

.edge-label {
  fill: var(--color-text-secondary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.nodes-layer {
  position: relative;
  z-index: 2;
}

.flow-node {
  position: absolute;
  width: 160px;
  min-height: 64px;
  padding: 12px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  text-align: center;
  transform: translate(-50%, 0);
  box-shadow: 0 4px 15px -3px rgba(0, 0, 0, 0.05), 0 2px 6px -2px rgba(0, 0, 0, 0.03);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease, border-color 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.flow-node:hover {
  transform: translate(-50%, -4px);
  box-shadow: 0 12px 20px -5px rgba(59, 130, 246, 0.15), 0 8px 10px -4px rgba(59, 130, 246, 0.1);
  border-color: #93c5fd;
}

.node-index {
  position: absolute;
  top: -10px;
  left: -10px;
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #3b82f6 0%, var(--color-info) 100%);
  color: white;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(37, 99, 235, 0.3);
  border: 2px solid #fff;
}

.node-content {
  width: 100%;
}

.flow-node strong {
  display: block;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--color-text-strong);
  margin-bottom: 4px;
}

.flow-node p {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-text-muted);
}

/* Specific Node Types */
.flow-node.start {
  border: 2px solid #3b82f6;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: 999px;
}

.flow-node.end {
  border: 2px solid var(--color-success);
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border-radius: 999px;
}

.flow-node.decision {
  border: 2px solid var(--color-warning);
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border-radius: 8px;
  clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
  padding: 20px;
  min-height: 80px;
}

.flow-node.decision:hover {
  transform: translate(-50%, -4px) scale(1.05);
}

.flow-node.danger {
  border: 2px solid var(--color-danger);
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
}
</style>
