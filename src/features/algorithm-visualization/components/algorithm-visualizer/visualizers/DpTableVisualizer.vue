<template>
  <div class="dp-table-visualizer">
    <div class="visualizer-meta">
      <div>
        <h3>动态规划表可视化</h3>
        <p>展示 DP 表格的逐格填入过程，高亮当前读写单元格。</p>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot active"></i>当前</span>
        <span class="legend-item"><i class="legend-dot success"></i>已完成</span>
      </div>
    </div>

    <div class="chart-shell">
      <div v-if="headers.length || values.length" class="dp-grid">
        <div v-if="headers.length" class="dp-row header">
          <span v-for="(header, index) in headers" :key="`h-${index}`" class="dp-cell header">
            {{ header }}
          </span>
        </div>
        <div v-for="(row, rowIndex) in values" :key="`r-${rowIndex}`" class="dp-row">
          <span
            v-for="(value, colIndex) in row"
            :key="`c-${rowIndex}-${colIndex}`"
            :class="['dp-cell', getCellTone(rowIndex, colIndex)]"
          >
            {{ value }}
          </span>
        </div>
      </div>

      <div v-else class="empty-state">
        等待 DP 表数据初始化...
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { VisualStep } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  initialState: any
  currentStep: VisualStep | null
  currentStepIndex: number
}>()

const headers = computed<string[]>(() => {
  const raw = props.currentStep?.payload?.headers
  return Array.isArray(raw) ? raw : []
})

const values = computed<Array<Array<string | number>>>(() => {
  const raw = props.currentStep?.payload?.values
  return Array.isArray(raw) ? raw : []
})

const highlighted = computed(() => {
  const raw = props.currentStep?.payload?.highlighted
  return Array.isArray(raw) ? raw : []
})

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
  gap: 16px;
  padding: 18px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95));
}

.visualizer-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.visualizer-meta h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 760;
  color: #0f172a;
}

.visualizer-meta p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #475569;
}

.legend-dot {
  width: 10px;
  height: 10px;
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
  background: rgba(220, 252, 231, 0.95);
  border: 1px solid #10b981;
}

.chart-shell {
  min-height: 0;
  border-radius: 24px;
  background: rgba(241, 245, 249, 0.62);
  border: 1px solid rgba(226, 232, 240, 0.96);
  padding: 16px;
  overflow: auto;
}

.dp-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dp-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(48px, 1fr));
  gap: 8px;
}

.dp-row.header {
  margin-bottom: 4px;
}

.dp-cell {
  display: grid;
  place-items: center;
  min-height: 44px;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.95);
  color: #0f172a;
  font-weight: 700;
}

.dp-cell.header {
  background: transparent;
  border-color: transparent;
  color: #64748b;
  font-size: 12px;
}

.dp-cell.active {
  border-color: rgba(37, 99, 235, 0.45);
  background: rgba(219, 234, 254, 0.9);
}

.dp-cell.success {
  border-color: rgba(16, 185, 129, 0.35);
  background: rgba(220, 252, 231, 0.92);
}

.empty-state {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #94a3b8;
}
</style>
