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
.stack-queue-visualizer { height: 100%; min-height: 0; display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 16px; padding: 18px; background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 26%), linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95)); }
.visualizer-meta { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.visualizer-meta h3 { margin: 0; font-size: 20px; font-weight: 760; color: #0f172a; }
.visualizer-meta p { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.legend { display: flex; gap: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #475569; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }
.legend-dot.default { background: #cbd5e1; border: 1px solid #94a3b8; }
.legend-dot.visited { background: rgba(220, 252, 231, 0.95); border: 1px solid #10b981; }
.chart-shell { min-height: 0; border-radius: 24px; background: rgba(241, 245, 249, 0.62); border: 1px solid rgba(226, 232, 240, 0.96); padding: 16px; }
.linear-strip { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-height: 200px; justify-content: center; }
.linear-strip.stack { flex-direction: column; align-items: center; }
.linear-node { min-width: 72px; display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 12px 8px 10px; border-radius: 18px; background: rgba(248, 250, 252, 0.92); border: 1px solid rgba(226, 232, 240, 0.95); }
.linear-node.visited { border-color: rgba(16, 185, 129, 0.35); background: rgba(236, 253, 245, 0.95); }
.node-value { font-size: 16px; font-weight: 700; color: #0f172a; }
.pointer-stack { min-height: 24px; display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.pointer-pill { display: inline-flex; align-items: center; min-height: 22px; padding: 0 8px; border-radius: 999px; font-size: 11px; font-weight: 800; }
.pointer-pill.accent { background: rgba(219, 234, 254, 0.9); color: #2563eb; }
.pointer-pill.warning { background: rgba(254, 243, 199, 0.92); color: #d97706; }
.pointer-pill.success { background: rgba(220, 252, 231, 0.92); color: #059669; }
.empty-state { height: 100%; min-height: 240px; display: flex; align-items: center; justify-content: center; font-size: 14px; color: #94a3b8; }
</style>
