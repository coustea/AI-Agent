<template>
  <div class="tree-visualizer">
    <div class="visualizer-meta">
      <div><h3>树可视化</h3><p>展示树节点的遍历和访问过程。</p></div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
      </div>
    </div>
    <div class="chart-shell">
      <div v-if="nodes.length" class="tree-grid">
        <div v-for="node in nodes" :key="node.id" :class="['tree-node', node.tone || 'default']" :style="nodeStyle(node)">
          <span class="node-label">{{ node.label }}</span>
        </div>
      </div>
      <div v-else class="empty-state">等待树数据初始化...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{ currentEvent: TraceEvent | null; currentStepIndex: number; events: TraceEvent[] }>()

const nodes = computed(() => { const raw = props.currentEvent?.state?.structure?.nodes; return Array.isArray(raw) ? raw : [] })

function nodeStyle(node: any) {
  return { left: `${(node.x ?? 0) * 80}px`, top: `${(node.y ?? 0) * 80}px` }
}
</script>

<style scoped>
.tree-visualizer { height: 100%; min-height: 0; display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 16px; padding: 18px; background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 26%), linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95)); }
.visualizer-meta { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.visualizer-meta h3 { margin: 0; font-size: 20px; font-weight: 760; color: #0f172a; }
.visualizer-meta p { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.legend { display: flex; gap: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #475569; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }
.legend-dot.default { background: #cbd5e1; border: 1px solid #94a3b8; }
.legend-dot.visited { background: rgba(220, 252, 231, 0.95); border: 1px solid #10b981; }
.chart-shell { min-height: 0; border-radius: 24px; background: rgba(241, 245, 249, 0.62); border: 1px solid rgba(226, 232, 240, 0.96); padding: 16px; overflow: auto; position: relative; }
.tree-grid { position: relative; min-height: 300px; }
.tree-node { position: absolute; min-width: 48px; min-height: 48px; display: grid; place-items: center; border-radius: 50%; background: rgba(248, 250, 252, 0.96); border: 2px solid rgba(226, 232, 240, 0.95); font-weight: 700; font-size: 14px; color: #0f172a; transform: translate(-50%, -50%); }
.tree-node.visited { border-color: #10b981; background: rgba(220, 252, 231, 0.95); color: #059669; }
.node-label { font-size: 14px; }
.empty-state { height: 100%; min-height: 240px; display: flex; align-items: center; justify-content: center; font-size: 14px; color: #94a3b8; }
</style>
