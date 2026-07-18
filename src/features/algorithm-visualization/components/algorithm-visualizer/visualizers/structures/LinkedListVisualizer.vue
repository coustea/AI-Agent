<template>
  <div class="linked-list-visualizer">
    <div class="chart-shell">
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
      </div>

      <div v-if="nodes.length" class="linear-strip">
        <div
          v-for="(node, index) in nodes"
          :key="node.id"
          :data-node-id="node.id"
          :class="['linear-node', node.tone || 'default']"
        >
          <span class="node-value">{{ node.label }}</span>
          <span class="node-next">
            <span class="node-arrow">→</span>
            {{ getNextLabel(node.next) }}
          </span>
          <div class="pointer-stack">
            <span v-for="pointer in getPointers(index)" :key="pointer.label" :class="['pointer-pill', pointer.tone || 'accent']">{{ pointer.label }}</span>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">等待链表节点数据初始化...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import type { TraceEvent, VisualNode, VisualPointer } from '@/features/algorithm-visualization/types'

const props = defineProps<{ currentEvent: TraceEvent | null; currentStepIndex: number; events: TraceEvent[]; onStepComplete?: () => void }>()

// 当前步骤的链表节点和指针数据
const nodes = computed<VisualNode[]>(() => { const raw = props.currentEvent?.state?.structure?.nodes; return Array.isArray(raw) ? raw as VisualNode[] : [] })
const pointers = computed<VisualPointer[]>(() => { const raw = props.currentEvent?.state?.structure?.pointers; return Array.isArray(raw) ? raw as VisualPointer[] : [] })
// 获取特定索引节点上的指针标签
function getPointers(index: number) {
  const nodeId = nodes.value[index]?.id
  return pointers.value.filter(pointer => (
    pointer.nodeId === nodeId || pointer.nodeIndex === index || pointer.itemIndex === index
  ))
}

function getNextLabel(nextId: string | null | undefined) {
  if (!nextId) return '∅'
  return nodes.value.find(node => node.id === nextId)?.label ?? nextId
}

// 动画完成通知：链表无 CSS 过渡，步骤变化后立即完成
watch(
  [() => props.currentStepIndex, () => props.currentEvent],
  () => {
    requestAnimationFrame(() => {
      props.onStepComplete?.()
    })
  },
)

onBeforeUnmount(() => {})
</script>

<style scoped>
.linked-list-visualizer {
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
  padding: 12px;
}

.linear-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 200px;
  justify-content: center;
}

.linear-node {
  min-width: 64px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border-radius: var(--radius-sm);
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

.node-arrow {
  font-size: 14px;
  color: var(--color-text-faint);
  margin-right: 3px;
}

.node-next {
  min-height: 20px;
  display: inline-flex;
  align-items: center;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
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
