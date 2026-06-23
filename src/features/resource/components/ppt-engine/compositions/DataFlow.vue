<template>
  <div class="composition data-flow">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="canvas-container ppt-card">
      <svg class="flow-svg" viewBox="0 0 800 450">
        <!-- Arrow marker -->
        <defs>
          <marker id="flow-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--ppt-accent)" />
          </marker>
        </defs>

        <!-- Connections (curves with labels) -->
        <g class="edges">
          <g v-for="(edge, idx) in edges" :key="`edge-${idx}`">
            <path
              :d="edge.d"
              stroke="var(--ppt-accent)"
              stroke-width="2"
              fill="none"
              marker-end="url(#flow-arrow)"
            />
            <text
              :x="edge.lx"
              :y="edge.ly"
              text-anchor="middle"
              fill="var(--ppt-text-secondary)"
              font-size="10"
              font-weight="bold"
            >
              {{ edge.label }}
            </text>
          </g>
        </g>

        <!-- Process Boxes -->
        <g class="nodes">
          <g
            v-for="node in positionedNodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
          >
            <rect
              x="-65"
              y="-20"
              width="130"
              height="40"
              rx="4"
              fill="var(--ppt-bg-secondary)"
              stroke="var(--ppt-text-primary)"
              stroke-width="2"
              class="flow-rect"
            />
            <text
              text-anchor="middle"
              dominant-baseline="middle"
              fill="var(--ppt-text-primary)"
              font-size="11"
              font-weight="bold"
            >
              {{ node.label }}
            </text>
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ResolvedSlide } from '../model/resolvedSlide'

const props = defineProps<{ slide: ResolvedSlide }>()

const positionedNodes = computed(() => {
  const elements = props.slide.elements
  const count = elements.length
  const width = 800
  const height = 450

  return elements.map((el, idx) => {
    const id = el.label || el.content || ''
    const x = ((idx + 0.5) / count) * width
    const y = height / 2
    return { id, label: el.content || '', x, y }
  })
})

const edges = computed(() => {
  const result: Array<{ d: string; lx: number; ly: number; label: string }> = []
  const nodes = positionedNodes.value
  const nodeMap = new Map<string, typeof nodes[0]>()
  nodes.forEach(n => nodeMap.set(n.id, n))

  const relations = props.slide.relations || []
  relations.forEach(rel => {
    const sourceNode = nodeMap.get(rel.source)
    const targetNode = nodeMap.get(rel.target)
    if (sourceNode && targetNode) {
      const dx = targetNode.x - sourceNode.x
      const dy = targetNode.y - sourceNode.y
      const len = Math.sqrt(dx * dx + dy * dy)
      if (len > 0) {
        const sx = sourceNode.x + (dx / len) * 65
        const sy = sourceNode.y + (dy / len) * 20
        const tx = targetNode.x - (dx / len) * 70
        const ty = targetNode.y - (dy / len) * 20
        const midX = (sx + tx) / 2
        const midY = (sy + ty) / 2
        result.push({
          d: `M ${sx} ${sy} L ${tx} ${ty}`,
          lx: midX,
          ly: midY - 8,
          label: rel.label || 'data',
        })
      }
    }
  })

  return result
})
</script>

<style scoped>
.data-flow {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 40px 60px;
  box-sizing: border-box;
}
.subtitle {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  margin-bottom: 24px;
  border-left: 3px solid var(--ppt-accent);
  padding-left: 12px;
}
.canvas-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 10px;
  background: var(--ppt-bg-secondary);
}
.flow-svg {
  width: 100%;
  height: 100%;
  max-height: 380px;
}
.flow-rect {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.05));
}
</style>
