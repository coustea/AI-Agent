<template>
  <div class="composition sequence-timeline">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="canvas-container ppt-card">
      <svg class="seq-svg" viewBox="0 0 800 450">
        <!-- Arrow marker -->
        <defs>
          <marker id="seq-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--ppt-accent)" />
          </marker>
        </defs>

        <!-- Participant Lifelines -->
        <g class="lifelines">
          <g v-for="part in participants" :key="part.id">
            <line
              :x1="part.x"
              y1="60"
              :x2="part.x"
              y2="400"
              stroke="var(--ppt-text-secondary)"
              stroke-width="1.5"
              stroke-dasharray="4 4"
            />
            <rect
              :x="part.x - 60"
              y="20"
              width="120"
              height="35"
              rx="4"
              fill="var(--ppt-bg-secondary)"
              stroke="var(--ppt-accent)"
              stroke-width="2"
            />
            <text
              :x="part.x"
              y="37"
              text-anchor="middle"
              dominant-baseline="middle"
              fill="var(--ppt-text-primary)"
              font-size="11"
              font-weight="bold"
            >
              {{ part.label }}
            </text>
          </g>
        </g>

        <!-- Message Arrows -->
        <g class="messages">
          <g v-for="(msg, idx) in messages" :key="`msg-${idx}`">
            <line
              :x1="msg.x1"
              :y1="msg.y"
              :x2="msg.x2"
              :y2="msg.y"
              stroke="var(--ppt-accent)"
              stroke-width="2"
              marker-end="url(#seq-arrow)"
            />
            <text
              :x="(msg.x1 + msg.x2) / 2"
              :y="msg.y - 8"
              text-anchor="middle"
              fill="var(--ppt-text-secondary)"
              font-size="10"
              font-weight="bold"
            >
              {{ msg.label }}
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

const participants = computed(() => {
  const elements = props.slide.elements
  const count = elements.length
  const width = 800

  return elements.map((el, idx) => {
    const id = el.label || el.content || ''
    const x = ((idx + 0.5) / count) * width
    return { id, label: el.content || '', x }
  })
})

const messages = computed(() => {
  const result: Array<{ x1: number; x2: number; y: number; label: string }> = []
  const parts = participants.value
  const partMap = new Map<string, typeof parts[0]>()
  parts.forEach(p => partMap.set(p.id, p))

  const relations = props.slide.relations || []
  const startY = 100
  const gapY = 50

  relations.forEach((rel, idx) => {
    const sourcePart = partMap.get(rel.source)
    const targetPart = partMap.get(rel.target)
    if (sourcePart && targetPart) {
      result.push({
        x1: sourcePart.x,
        x2: targetPart.x,
        y: startY + idx * gapY,
        label: rel.label || 'call()',
      })
    }
  })

  return result
})
</script>

<style scoped>
.sequence-timeline {
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
.seq-svg {
  width: 100%;
  height: 100%;
  max-height: 380px;
}
</style>
