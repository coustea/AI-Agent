<template>
  <div class="composition state-transition">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="canvas-container ppt-card">
      <svg class="state-svg" viewBox="0 0 800 450">
        <!-- Arrow marker -->
        <defs>
          <marker id="state-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--ppt-accent)" />
          </marker>
        </defs>

        <!-- Transitions (lines with label) -->
        <g class="transitions">
          <g v-for="(trans, idx) in transitions" :key="`trans-${idx}`">
            <path
              :d="trans.d"
              stroke="var(--ppt-accent)"
              stroke-width="2"
              fill="none"
              marker-end="url(#state-arrow)"
            />
            <rect
              :x="trans.lx - 35"
              :y="trans.ly - 10"
              width="70"
              height="20"
              rx="4"
              fill="var(--ppt-bg-secondary)"
              stroke="var(--ppt-border)"
              stroke-width="1"
            />
            <text
              :x="trans.lx"
              :y="trans.ly"
              text-anchor="middle"
              dominant-baseline="middle"
              fill="var(--ppt-text-secondary)"
              font-size="10"
              font-weight="bold"
            >
              {{ trans.label }}
            </text>
          </g>
        </g>

        <!-- States -->
        <g class="states">
          <g
            v-for="state in positionedStates"
            :key="state.id"
            :transform="`translate(${state.x}, ${state.y})`"
          >
            <circle
              r="30"
              fill="var(--ppt-bg-secondary)"
              stroke="var(--ppt-text-primary)"
              stroke-width="3"
              class="state-circle"
            />
            <circle
              v-if="state.isDoubleBorder"
              r="24"
              fill="none"
              stroke="var(--ppt-text-primary)"
              stroke-width="1"
            />
            <text
              text-anchor="middle"
              dominant-baseline="middle"
              fill="var(--ppt-text-primary)"
              font-size="11"
              font-weight="bold"
            >
              {{ state.label }}
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

const positionedStates = computed(() => {
  const elements = props.slide.elements
  const count = elements.length
  const width = 800
  const height = 450

  return elements.map((el, idx) => {
    const id = el.label || el.content || ''
    // Linear horizontal distribution with minor vertical waves
    const x = ((idx + 0.5) / count) * width
    const y = height / 2 + (idx % 2 === 0 ? -30 : 30)
    // Make first state start and last state double bordered (acceptance state)
    const isDoubleBorder = idx === count - 1
    return { id, label: el.content || '', x, y, isDoubleBorder }
  })
})

const transitions = computed(() => {
  const result: Array<{ d: string; lx: number; ly: number; label: string }> = []
  const states = positionedStates.value
  const stateMap = new Map<string, typeof states[0]>()
  states.forEach(s => stateMap.set(s.id, s))

  const relations = props.slide.relations || []
  relations.forEach(rel => {
    const sourceNode = stateMap.get(rel.source)
    const targetNode = stateMap.get(rel.target)
    if (sourceNode && targetNode) {
      const dx = targetNode.x - sourceNode.x
      const dy = targetNode.y - sourceNode.y
      const len = Math.sqrt(dx * dx + dy * dy)
      if (len > 0) {
        const sx = sourceNode.x + (dx / len) * 30
        const sy = sourceNode.y + (dy / len) * 30
        const tx = targetNode.x - (dx / len) * 35
        const ty = targetNode.y - (dy / len) * 35
        const midX = (sx + tx) / 2
        const midY = (sy + ty) / 2 - 20
        result.push({
          d: `M ${sx} ${sy} Q ${midX} ${midY} ${tx} ${ty}`,
          lx: midX,
          ly: midY - 5,
          label: rel.label || 'transition',
        })
      }
    }
  })

  return result
})
</script>

<style scoped>
.state-transition {
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
.state-svg {
  width: 100%;
  height: 100%;
  max-height: 380px;
}
.state-circle {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.05));
}
</style>
