<template>
  <div class="composition definition-focus">
    <div class="focus-pane">
      <div v-for="el in slide.slots.focus || []" :key="el.content || ''" class="definition-card ppt-card">
        <div class="concept-label">{{ el.label || 'CORE CONCEPT' }}</div>
        <div class="concept-content">{{ el.content }}</div>
      </div>
    </div>
    <div class="notes-pane">
      <div class="key-message">{{ slide.key_message }}</div>
      <div class="details-list">
        <div v-for="el in slide.slots.main || []" :key="el.content || ''" class="detail-item">
          <span class="bullet">✦</span>
          <span class="detail-text">{{ el.content }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResolvedSlide } from '../model/resolvedSlide'
defineProps<{ slide: ResolvedSlide }>()
</script>

<style scoped>
.definition-focus {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  height: 100%;
  padding: 40px 60px;
  box-sizing: border-box;
  align-items: center;
}
.focus-pane {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.definition-card {
  border-left: 6px solid var(--ppt-accent);
  padding: 30px;
}
.concept-label {
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--ppt-accent);
  letter-spacing: 0.1em;
  margin-bottom: 12px;
}
.concept-content {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.4;
  color: var(--ppt-text-primary);
}
.notes-pane {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.key-message {
  font-size: 1.15rem;
  font-weight: 600;
  line-height: 1.5;
  color: var(--ppt-text-primary);
  border-bottom: 1px solid var(--ppt-border);
  padding-bottom: 12px;
}
.details-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.detail-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.bullet {
  color: var(--ppt-accent);
  font-weight: bold;
}
.detail-text {
  font-size: 1rem;
  line-height: 1.5;
  color: var(--ppt-text-secondary);
}
</style>
