<template>
  <div class="composition knowledge-map">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="canvas-container ppt-card">
      <svg class="map-svg" viewBox="0 0 800 450">
        <!-- Connections -->
        <g class="edges">
          <line
            v-for="(edge, idx) in edges"
            :key="`edge-${idx}`"
            :x1="edge.x1"
            :y1="edge.y1"
            :x2="edge.x2"
            :y2="edge.y2"
            stroke="var(--ppt-accent)"
            stroke-width="1.5"
            stroke-dasharray="2 2"
          />
        </g>

        <!-- Concept Nodes -->
        <g class="nodes">
          <g
            v-for="node in positionedNodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
          >
            <rect
              x="-60"
              y="-18"
              width="120"
              height="36"
              rx="18"
              fill="var(--ppt-bg-secondary)"
              stroke="var(--ppt-accent)"
              stroke-width="2"
              class="map-rect"
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
    // Arrange in a soft spiral/scatter layout
    const angle = (idx / count) * 2 * Math.PI
    const r = 100 + (idx % 2) * 50
    const x = width / 2 + Math.cos(angle) * r
    const y = height / 2 + Math.sin(angle) * (r * 0.7)
    return { id, label: el.content || '', x, y }
  })
})

const edges = computed(() => {
  const result: Array<{ x1: number; y1: number; x2: number; y2: number }> = []
  const nodes = positionedNodes.value
  const nodeMap = new Map<string, typeof nodes[0]>()
  nodes.forEach(n => nodeMap.set(n.id, n))

  const relations = props.slide.relations || []
  relations.forEach(rel => {
    const sourceNode = nodeMap.get(rel.source)
    const targetNode = nodeMap.get(rel.target)
    if (sourceNode && targetNode) {
      result.push({
        x1: sourceNode.x,
        y1: sourceNode.y,
        x2: targetNode.x,
        y2: targetNode.y,
      })
    }
  })

  return result
})
</script>

<style scoped>
.knowledge-map {
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
.map-svg {
  width: 100%;
  height: 100%;
  max-height: 380px;
}
.map-rect {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.05));
}
</style>
