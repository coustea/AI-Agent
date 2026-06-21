<template>
  <div class="block-table-wrap">
    <table class="block-table">
      <thead>
        <tr>
          <th v-for="column in block.columns" :key="column">{{ column }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
          <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { TableBlock } from '../../types/ppt'

defineProps<{
  block: TableBlock
}>()
</script>

<style scoped>
.block-table-wrap {
  width: 100%;
  overflow: auto;
}

.block-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}

.block-table th,
.block-table td {
  padding: 10px 12px;
  border: 1px solid var(--ppt-border);
  text-align: left;
}

.block-table th {
  background: var(--ppt-bg-tertiary);
  color: var(--ppt-text-primary);
  font-weight: 800;
}

.block-table td {
  color: var(--ppt-text-secondary);
}
</style>
