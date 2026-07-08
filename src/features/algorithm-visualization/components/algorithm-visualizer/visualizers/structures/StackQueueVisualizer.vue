<template>
  <div class="stack-queue-visualizer">
    <div class="visualizer-meta">
      <div>
        <h3>{{ modeLabel }}可视化</h3>
        <p>展示{{ modeLabel }}的入队/出队过程，支持指针标注。</p>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已处理</span>
      </div>
    </div>

    <div class="chart-shell">
      <div v-if="items.length" :class="['linear-strip', mode]">
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
import { computed } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  currentEvent: TraceEvent | null
  currentStepIndex: number
  events: TraceEvent[]
}>()

const mode = computed<'stack' | 'queue'>(() => {
  const m = props.currentEvent?.state?.structure?.mode
  return m === 'stack' || m === 'queue' ? m : 'stack'
})
const modeLabel = computed(() => mode.value === 'queue' ? '队列' : '栈')

const items = computed(() => {
  const raw = props.currentEvent?.state?.structure?.items
  return Array.isArray(raw) ? raw : []
})

const pointers = computed(() => {
  const raw = props.currentEvent?.state?.structure?.pointers
  return Array.isArray(raw) ? raw : []
})

function getPointers(index: number) {
  return pointers.value.filter((p: any) => p.nodeIndex === index || p.itemIndex === index)
}
</script>

<style scoped>
.stack-queue-visualizer {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  background: #ffffff;
}

.visualizer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.visualizer-meta h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.visualizer-meta p {
  margin: 2px 0 0;
  font-size: 11px;
  color: #64748b;
}

.legend {
  display: flex;
  gap: 8px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #475569;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.default {
  background: #cbd5e1;
  border: 1px solid #94a3b8;
}

.legend-dot.visited {
  background: #ecfdf5;
  border: 1px solid #10b981;
}

.chart-shell {
  min-height: 0;
  border-radius: 4px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
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
  background: #ffffff;
  border: 1px solid #cbd5e1;
}

.linear-node.visited {
  border-color: #10b981;
  background: #ecfdf5;
}

.node-value {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
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
  background: #eff6ff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
}

.pointer-pill.warning {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}

.pointer-pill.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.empty-state {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #94a3b8;
}
</style>
