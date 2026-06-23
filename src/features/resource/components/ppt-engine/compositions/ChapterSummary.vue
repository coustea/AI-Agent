<template>
  <div class="composition chapter-summary">
    <h2 class="title">{{ slide.title }}</h2>
    <div class="key-message-box">
      <p class="key-message">{{ slide.key_message }}</p>
    </div>
    <div class="summary-list">
      <div v-for="el in slide.elements" :key="el.content || ''" class="summary-item ppt-card">
        <div class="check-icon">✓</div>
        <div class="summary-text">{{ el.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResolvedSlide } from '../model/resolvedSlide'
defineProps<{ slide: ResolvedSlide }>()
</script>

<style scoped>
.chapter-summary {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  padding: 60px 80px;
  box-sizing: border-box;
}
.title {
  font-size: 2.8rem;
  font-weight: 800;
  color: var(--ppt-text-primary);
  margin: 0 0 16px;
}
.key-message-box {
  margin-bottom: 30px;
}
.key-message {
  font-size: 1.25rem;
  color: var(--ppt-text-secondary);
  line-height: 1.6;
  margin: 0;
}
.summary-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.summary-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-left: 4px solid var(--ppt-accent);
}
.check-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--ppt-badge-bg);
  color: var(--ppt-badge-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.9rem;
}
.summary-text {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--ppt-text-primary);
}
</style>
