<template>
  <div class="block-table-wrap ppt-card">
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
  overflow: hidden;
  padding: 0;
  border-radius: var(--ppt-radius-md);
  border: 1px solid var(--ppt-border);
  box-shadow: var(--ppt-shadow-card);
}

.block-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.98rem;
  text-align: left;
}

.block-table th,
.block-table td {
  padding: 16px 20px;
  border-bottom: 1px solid var(--ppt-border);
}

.block-table th {
  background: rgba(37, 99, 235, 0.04);
  color: var(--ppt-accent);
  font-weight: 800;
  font-size: 1.02rem;
  letter-spacing: 0.05em;
  border-bottom: 2px solid var(--ppt-border);
}

.block-table tr:last-child td {
  border-bottom: none;
}

.block-table tr:nth-child(even) td {
  background: rgba(148, 163, 184, 0.02);
}

.block-table td {
  color: var(--ppt-text-secondary);
  line-height: 1.5;
}
</style>
