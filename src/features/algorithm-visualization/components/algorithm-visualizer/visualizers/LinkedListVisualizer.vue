<template>
  <div class="linked-list-visualizer">
    <div class="visualizer-meta">
      <div><h3>链表可视化</h3><p>展示链表节点的插入、删除、遍历过程，支持指针标注。</p></div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
      </div>
    </div>
    <div class="chart-shell">
      <div v-if="nodes.length" class="linear-strip">
        <div v-for="(node, index) in nodes" :key="node.id" :class="['linear-node', node.tone || 'default']">
          <span class="node-value">{{ node.label }}</span>
          <span v-if="index < nodes.length - 1" class="node-arrow">→</span>
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
import { computed } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{ currentEvent: TraceEvent | null; currentStepIndex: number; events: TraceEvent[] }>()

const nodes = computed(() => { const raw = props.currentEvent?.state?.structure?.nodes; return Array.isArray(raw) ? raw : [] })
const pointers = computed(() => { const raw = props.currentEvent?.state?.structure?.pointers; return Array.isArray(raw) ? raw : [] })
function getPointers(index: number) { return pointers.value.filter((p: any) => p.nodeIndex === index || p.itemIndex === index) }
</script>

<style scoped>
.linked-list-visualizer {
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

.node-arrow {
  font-size: 14px;
  color: #94a3b8;
  align-self: center;
  margin: 0 4px;
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
