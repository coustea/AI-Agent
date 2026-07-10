<template>
  <div class="dp-table-visualizer">
    <div class="chart-shell">
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot active"></i>当前</span>
        <span class="legend-item"><i class="legend-dot success"></i>已完成</span>
      </div>

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

// DP 表的表头、数值网格、高亮单元格坐标
const headers = computed<string[]>(() => { const raw = props.currentEvent?.state?.structure?.headers; return Array.isArray(raw) ? raw : [] })
const values = computed<Array<Array<string | number>>>(() => { const raw = props.currentEvent?.state?.structure?.values; return Array.isArray(raw) ? raw : [] })
const highlighted = computed(() => { const raw = props.currentEvent?.state?.structure?.highlighted; return Array.isArray(raw) ? raw : [] })

// 获取单元格的颜色主题（在 highlighted 列表中查找）
function getCellTone(row: number, col: number) {
  const matched = highlighted.value.find((item: any) => item.row === row && item.col === col)
  return matched?.tone || ''
}
</script>

<style scoped>
.dp-table-visualizer {
  height: 100%;
  min-height: 0;
  display: flex;
  padding: 12px;
  background: transparent;
}

.legend {
  position: sticky;
  top: 0;
  z-index: 1;
  width: fit-content;
  margin-left: auto;
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-surface) 86%, transparent);
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

.legend-dot.active {
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary);
}

.legend-dot.success {
  background: var(--color-success-soft);
  border: 1px solid var(--color-success);
}

.chart-shell {
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
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
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  font-weight: 600;
  font-size: 13px;
  font-family: var(--font-mono);
}

.dp-cell.header {
  background: transparent;
  border-color: transparent;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 500;
}

.dp-cell.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.dp-cell.success {
  border-color: var(--color-success);
  background: var(--color-success-soft);
  color: var(--color-success);
}

.empty-state {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--color-text-faint);
  font-family: var(--font-mono);
}
</style>
