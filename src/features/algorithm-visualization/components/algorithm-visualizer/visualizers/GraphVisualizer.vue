<template>
  <div class="graph-visualizer">
    <div class="visualizer-meta">
      <div><h3>图可视化</h3><p>展示图节点的遍历和边访问过程。</p></div>
    </div>
    <div class="chart-shell">
      <div v-if="nodes.length" class="graph-grid">
        <div v-for="node in nodes" :key="node.id" :class="['graph-node', node.tone || 'default']" :style="nodeStyle(node)">
          <span>{{ node.label }}</span>
        </div>
      </div>
      <div v-else class="empty-state">等待图数据初始化...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{ currentEvent: TraceEvent | null; currentStepIndex: number; events: TraceEvent[] }>()
const nodes = computed(() => { const raw = props.currentEvent?.state?.structure?.nodes; return Array.isArray(raw) ? raw : [] })
const edges = computed(() => { const raw = props.currentEvent?.state?.structure?.edges; return Array.isArray(raw) ? raw : [] })
function nodeStyle(node: any) { return { left: `${(node.x ?? 0) * 80}px`, top: `${(node.y ?? 0) * 80}px` } }
</script>

<style scoped>
.graph-visualizer { height: 100%; min-height: 0; display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 16px; padding: 18px; background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 26%), linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95)); }
.visualizer-meta { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.visualizer-meta h3 { margin: 0; font-size: 20px; font-weight: 760; color: #0f172a; }
.visualizer-meta p { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.chart-shell { min-height: 0; border-radius: 24px; background: rgba(241, 245, 249, 0.62); border: 1px solid rgba(226, 232, 240, 0.96); padding: 16px; overflow: auto; position: relative; }
.graph-grid { position: relative; min-height: 300px; }
.graph-node { position: absolute; min-width: 48px; min-height: 48px; display: grid; place-items: center; border-radius: 50%; background: rgba(248, 250, 252, 0.96); border: 2px solid rgba(226, 232, 240, 0.95); font-weight: 700; font-size: 14px; color: #0f172a; transform: translate(-50%, -50%); }
.graph-node.visited { border-color: #10b981; background: rgba(220, 252, 231, 0.95); color: #059669; }
.empty-state { height: 100%; min-height: 240px; display: flex; align-items: center; justify-content: center; font-size: 14px; color: #94a3b8; }
</style>
