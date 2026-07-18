<template>
  <div class="stack-queue-visualizer">
    <div class="chart-shell">
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已处理</span>
      </div>

      <div v-if="currentValue" class="current-token">
        <span>当前字符</span>
        <code>{{ currentValue }}</code>
      </div>

      <div v-if="items.length" ref="containerRef" :class="['linear-strip', mode]" @transitionend="handleTransitionEvent">
        <div
          v-for="(item, index) in items"
          :key="item.id"
          :class="['linear-node', item.tone || 'default']"
        >
          <span class="node-value">{{ item.label }}</span>
          <div class="pointer-stack">
            <span
              v-for="pointer in getPointers(index)"
              :key="pointer.label"
              :class="['pointer-pill', pointer.tone || 'accent']"
            >
              {{ pointer.label }}
            </span>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        等待{{ modeLabel }}数据初始化...
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { TraceEvent, VisualPointer } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  currentEvent: TraceEvent | null
  currentStepIndex: number
  events: TraceEvent[]
  onStepComplete?: () => void
}>()

// 栈/队列模式（降级为 stack）
const mode = computed<'stack' | 'queue'>(() => {
  const m = props.currentEvent?.state?.structure?.mode
  return m === 'stack' || m === 'queue' ? m : 'stack'
})
const modeLabel = computed(() => mode.value === 'queue' ? '队列' : '栈')

// 当前步骤的数据项和指针
const items = computed(() => {
  const raw = props.currentEvent?.state?.structure?.items
  return Array.isArray(raw) ? raw : []
})
const pointers = computed(() => {
  const raw = props.currentEvent?.state?.structure?.pointers
  return Array.isArray(raw) ? raw : []
})
const currentValue = computed(() => {
  const value = props.currentEvent?.state?.structure?.currentValue
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
})

// 获取特定索引上的指针标签
function getPointers(index: number) {
  return (pointers.value as VisualPointer[]).filter(pointer => (
    pointer.nodeIndex === index || pointer.itemIndex === index
  ))
}

// 动画完成通知：监听 CSS transitionend 事件，防抖后调用 onStepComplete
const containerRef = ref<HTMLElement | null>(null)
let transitionDebounceTimer: ReturnType<typeof setTimeout> | null = null
let hasActiveTransition = false

function onTransitionEnd() {
  if (transitionDebounceTimer !== null) {
    clearTimeout(transitionDebounceTimer)
  }
  transitionDebounceTimer = setTimeout(() => {
    hasActiveTransition = false
    props.onStepComplete?.()
  }, 60)
}

function handleTransitionEvent() {
  hasActiveTransition = true
  onTransitionEnd()
}

watch(
  [() => props.currentStepIndex, () => props.currentEvent],
  () => {
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    if (reducedMotion || !containerRef.value) {
      requestAnimationFrame(() => {
        if (!hasActiveTransition) {
          props.onStepComplete?.()
        }
      })
      return
    }
    if (transitionDebounceTimer !== null) {
      clearTimeout(transitionDebounceTimer)
    }
    transitionDebounceTimer = setTimeout(() => {
      hasActiveTransition = false
      props.onStepComplete?.()
    }, 350)
  },
)

onBeforeUnmount(() => {
  if (transitionDebounceTimer !== null) {
    clearTimeout(transitionDebounceTimer)
  }
})
</script>

<style scoped>
.stack-queue-visualizer {
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
  background: color-mix(in srgb, var(--color-surface) 82%, transparent);
  backdrop-filter: blur(6px);
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

.chart-shell {
  position: relative;
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: 48px 12px 12px;
}

.current-token {
  position: absolute;
  top: 12px;
  left: 14px;
  min-height: 26px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-secondary);
  font-size: 11px;
}

.current-token code {
  min-width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  padding: 0 7px;
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 700;
}

.linear-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 200px;
  justify-content: center;
}

.linear-strip.stack {
  flex-direction: column;
  align-items: center;
}

.linear-node {
  min-width: 64px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border-radius: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.linear-node.visited {
  border-color: var(--color-success);
  background: var(--color-success-soft);
}

.node-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-strong);
}

.pointer-stack {
  min-height: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
}

.pointer-pill {
  display: inline-flex;
  align-items: center;
  padding: 0 6px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 600;
}

.pointer-pill.accent {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border: 1px solid var(--color-primary-border);
}

.pointer-pill.warning {
  background: var(--color-warning-soft);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.pointer-pill.success {
  background: var(--color-success-soft);
  color: var(--color-success);
  border: 1px solid var(--color-success);
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
</style>
