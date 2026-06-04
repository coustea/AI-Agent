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
  padding: 18px 14px;
  border-radius: 12px;
  text-align: center;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
  transition: transform 0.2s ease;
}

.entity:hover {
  transform: translateY(-2px);
}

.entity.left {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}

.entity.right {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
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
  padding: 8px 12px;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 1px solid #fcd34d;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  color: #92400e;
  box-shadow: 0 0 15px rgba(252, 211, 77, 0.4);
  z-index: 1;
}

.dimensions-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 8px;
  font-size: 14px;
}

.dimensions-table th,
.dimensions-table td {
  padding: 12px 16px;
  text-align: left;
}

.dimensions-table th {
  font-weight: 600;
  color: #334155;
  padding-bottom: 4px;
  border-bottom: 2px solid rgba(226, 232, 240, 0.5);
}

.dimensions-table tbody tr {
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  transition: all 0.2s ease;
}

.dimensions-table tbody tr:hover {
  transform: scale(1.01);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
}

.dimensions-table td {
  border-top: 1px solid #f1f5f9;
  border-bottom: 1px solid #f1f5f9;
}

.dimensions-table td:first-child {
  border-left: 1px solid #f1f5f9;
  border-top-left-radius: 8px;
  border-bottom-left-radius: 8px;
}

.dimensions-table td:last-child {
  border-right: 1px solid #f1f5f9;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
}

.dimensions-table .dim-name {
  background: rgba(248, 250, 252, 0.6);
  font-weight: 600;
  color: #475569;
}

.visual-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
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
