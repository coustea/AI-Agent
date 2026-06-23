<template>
  <div class="composition component-architecture">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="canvas-container ppt-card">
      <svg class="architecture-svg" viewBox="0 0 800 450">
        <!-- Arrow marker -->
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--ppt-accent)" />
          </marker>
        </defs>

        <!-- Connections -->
        <g class="edges">
          <path
            v-for="(edge, idx) in edges"
            :key="`edge-${idx}`"
            :d="edge.d"
            stroke="var(--ppt-accent)"
            stroke-width="2"
            fill="none"
            marker-end="url(#arrow)"
          />
        </g>

        <!-- Components -->
        <g class="nodes">
          <g
            v-for="node in positionedNodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
          >
            <rect
              x="-70"
              y="-25"
              width="140"
              height="50"
              rx="6"
              fill="var(--ppt-bg-secondary)"
              stroke="var(--ppt-text-secondary)"
              stroke-width="2"
              class="comp-rect"
            />
            <text
              text-anchor="middle"
              dominant-baseline="middle"
              fill="var(--ppt-text-primary)"
              font-size="12"
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

  // Arrange nodes in circle/columns
  return elements.map((el, idx) => {
    const id = el.label || el.content || ''
    const angle = (idx / count) * 2 * Math.PI
    const x = width / 2 + Math.cos(angle) * 220
    const y = height / 2 + Math.sin(angle) * 140
    return { id, label: el.content || '', x, y }
  })
})

const edges = computed(() => {
  const result: Array<{ d: string }> = []
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
        const sx = sourceNode.x + (dx / len) * 70
        const sy = sourceNode.y + (dy / len) * 25
        const tx = targetNode.x - (dx / len) * 75
        const ty = targetNode.y - (dy / len) * 28
        result.push({
          d: `M ${sx} ${sy} Q ${(sx + tx) / 2 + 10} ${(sy + ty) / 2 + 10} ${tx} ${ty}`,
        })
      }
    }
  })

  return result
})
</script>

<style scoped>
.component-architecture {
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
.architecture-svg {
  width: 100%;
  height: 100%;
  max-height: 380px;
}
.comp-rect {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.05));
}
</style>
