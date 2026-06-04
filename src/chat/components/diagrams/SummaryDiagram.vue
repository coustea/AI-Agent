<template>
  <div class="summary-diagram">
    <div class="cards-grid">
      <div v-for="card in payload.cards" :key="card.title" class="summary-card">
        <strong class="card-title">{{ card.title }}</strong>
        <p class="card-desc">{{ card.short_desc }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SummaryPayload } from '@/chat/types/chat'

defineProps<{
  payload: SummaryPayload
}>()
</script>

<style scoped>
.summary-diagram {
  display: grid;
  gap: 12px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.summary-card {
  padding: 18px 20px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #3b82f6;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  transition: transform 0.3s ease, box-shadow 0.3s ease, border-left-color 0.3s ease;
  position: relative;
}

.summary-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
  border-left-color: #06b6d4;
}

.card-title {
  display: block;
  margin-bottom: 8px;
  font-size: 16px;
  font-weight: 800;
  color: var(--c-ink, #0f172a);
  overflow-wrap: break-words;
  word-break: break-all;
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: var(--c-muted, #64748b);
  line-height: 1.6;
  overflow-wrap: break-words;
  word-break: break-all;
}
</style>
