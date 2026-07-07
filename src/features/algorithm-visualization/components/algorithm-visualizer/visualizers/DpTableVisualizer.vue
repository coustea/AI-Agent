<template>
  <div class="dp-table-visualizer">
    <div class="visualizer-meta">
      <div><h3>动态规划表可视化</h3><p>展示 DP 表格的逐格填入过程，高亮当前读写单元格。</p></div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot active"></i>当前</span>
        <span class="legend-item"><i class="legend-dot success"></i>已完成</span>
      </div>
    </div>
    <div class="chart-shell">
      <div v-if="headers.length || values.length" class="dp-grid">
        <div v-if="headers.length" class="dp-row header">
          <span v-for="(header, index) in headers" :key="`h-${index}`" class="dp-cell header">{{ header }}</span>
        </div>
        <div v-for="(row, rowIndex) in values" :key="`r-${rowIndex}`" class="dp-row">
          <span v-for="(value, colIndex) in row" :key="`c-${rowIndex}-${colIndex}`" :class="['dp-cell', getCellTone(rowIndex, colIndex)]">{{ value }}</span>
        </div>
      </div>
      <div v-else class="empty-state">等待 DP 表数据初始化...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{ currentEvent: TraceEvent | null; currentStepIndex: number; events: TraceEvent[] }>()

const headers = computed<string[]>(() => { const raw = props.currentEvent?.state?.structure?.headers; return Array.isArray(raw) ? raw : [] })
const values = computed<Array<Array<string | number>>>(() => { const raw = props.currentEvent?.state?.structure?.values; return Array.isArray(raw) ? raw : [] })
const highlighted = computed(() => { const raw = props.currentEvent?.state?.structure?.highlighted; return Array.isArray(raw) ? raw : [] })

function getCellTone(row: number, col: number) {
  const matched = highlighted.value.find((item: any) => item.row === row && item.col === col)
  return matched?.tone || ''
}
</script>

<style scoped>
.dp-table-visualizer {
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

.legend-dot.active {
  background: #93c5fd;
  border: 1px solid #2563eb;
}

.legend-dot.success {
  background: #ecfdf5;
  border: 1px solid #10b981;
}

.chart-shell {
  min-height: 0;
  border-radius: 4px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 12px;
  overflow: auto;
}

.dp-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dp-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(44px, 1fr));
  gap: 4px;
}

.dp-row.header {
  margin-bottom: 2px;
}

.dp-cell {
  display: grid;
  place-items: center;
  min-height: 38px;
  border-radius: 4px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #334155;
  font-weight: 600;
  font-size: 13px;
}

.dp-cell.header {
  background: transparent;
  border-color: transparent;
  color: #64748b;
  font-size: 11px;
  font-weight: 500;
}

.dp-cell.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #2563eb;
}

.dp-cell.success {
  border-color: #10b981;
  background: #ecfdf5;
  color: #047857;
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
