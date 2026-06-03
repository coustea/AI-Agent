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
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #2563eb;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  transition: box-shadow 0.2s ease;
}

.summary-card:hover {
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.1);
}

.card-title {
  display: block;
  margin-bottom: 6px;
  font-size: 15px;
  font-weight: 700;
  color: var(--c-ink, #111827);
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: var(--c-muted, #64748b);
  line-height: 1.5;
}
</style>
