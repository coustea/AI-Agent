<template>
  <div class="comparison-diagram">
    <div class="entities-row">
      <div class="entity left">
        <span class="entity-name">{{ payload.left_entity.name }}</span>
        <span class="entity-core">{{ payload.left_entity.core_label }}</span>
        <p class="entity-desc">{{ payload.left_entity.short_desc }}</p>
      </div>
      <div class="vs-badge">VS</div>
      <div class="entity right">
        <span class="entity-name">{{ payload.right_entity.name }}</span>
        <span class="entity-core">{{ payload.right_entity.core_label }}</span>
        <p class="entity-desc">{{ payload.right_entity.short_desc }}</p>
      </div>
    </div>

    <table class="dimensions-table">
      <thead>
        <tr>
          <th>维度</th>
          <th>{{ payload.left_entity.name }}</th>
          <th>{{ payload.right_entity.name }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="dim in payload.dimensions" :key="dim.name">
          <td class="dim-name">{{ dim.name }}</td>
          <td class="dim-left">{{ dim.left }}</td>
          <td class="dim-right">{{ dim.right }}</td>
        </tr>
      </tbody>
    </table>

    <div class="visual-summary">
      <span class="keyword left-keyword">{{ payload.visual_summary.left_keyword }}</span>
      <span class="center-conclusion">{{ payload.visual_summary.center_conclusion }}</span>
      <span class="keyword right-keyword">{{ payload.visual_summary.right_keyword }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ComparisonPayload } from '@/chat/types/chat'

defineProps<{
  payload: ComparisonPayload
}>()
</script>

<style scoped>
.comparison-diagram {
  display: grid;
  gap: 16px;
}

.entities-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 12px;
  align-items: center;
}

.entity {
  display: grid;
  gap: 6px;
  padding: 14px;
  background: var(--c-bg, #f8fafc);
  border: 1px solid var(--c-border, #d8dee9);
  border-radius: 8px;
  text-align: center;
}

.entity.left {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.entity.right {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.entity-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--c-ink, #111827);
}

.entity-core {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-primary, #2563eb);
}

.entity-desc {
  margin: 0;
  font-size: 12px;
  color: var(--c-muted, #64748b);
}

.vs-badge {
  padding: 6px 10px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  color: #92400e;
}

.dimensions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.dimensions-table th,
.dimensions-table td {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  text-align: left;
}

.dimensions-table th {
  background: #f1f5f9;
  font-weight: 600;
  color: #334155;
}

.dimensions-table .dim-name {
  background: #f8fafc;
  font-weight: 600;
  color: #475569;
}

.visual-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.keyword {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.left-keyword {
  background: #dbeafe;
  color: #1d4ed8;
}

.right-keyword {
  background: #dcfce7;
  color: #15803d;
}

.center-conclusion {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-ink, #111827);
  text-align: center;
}
</style>
