<template>
  <div class="summary-diagram">
    <div class="summary-header">
      <div class="header-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
        </svg>
      </div>
      <h3 class="header-title">核心总结与要点归纳</h3>
      <div class="header-bg"></div>
    </div>

    <div class="cards-layout">
      <div v-for="(card, idx) in payload.cards" :key="card.title" class="summary-card" :class="`theme-${idx % 4}`">
        <div class="card-number">{{ String(idx + 1).padStart(2, '0') }}</div>
        <div class="card-content">
          <strong class="card-title">{{ card.title }}</strong>
          <p class="card-desc">{{ card.short_desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SummaryPayload } from '@/features/chat/types/chat'

defineProps<{
  payload: SummaryPayload
}>()
</script>

<style scoped>
.summary-diagram {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 8px;
}

.summary-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 15px -3px rgba(0,0,0,0.1);
}

.header-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--color-text-strong) 0%, var(--color-text) 100%);
  z-index: 0;
}

.header-bg::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 50%;
  background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.2));
  transform: skewX(-20deg) translateX(20%);
}

.header-icon {
  position: relative;
  z-index: 1;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-warning), #d97706);
  color: white;
  border-radius: 8px;
  box-shadow: 0 0 15px rgba(245, 158, 11, 0.4);
}

.header-icon svg {
  width: 18px;
  height: 18px;
}

.header-title {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--color-surface);
  letter-spacing: 0.05em;
}

.cards-layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.summary-card {
  position: relative;
  display: flex;
  gap: 16px;
  padding: 20px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  overflow: hidden;
}

.summary-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.08);
}

.summary-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
}

.theme-0::before { background: #3b82f6; }
.theme-1::before { background: var(--color-success); }
.theme-2::before { background: var(--color-warning); }
.theme-3::before { background: #8b5cf6; }

.card-number {
  font-size: 24px;
  font-weight: 900;
  font-family: var(--font-mono);
  opacity: 0.15;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  transform: rotate(180deg);
  display: flex;
  align-items: center;
}

.theme-0 .card-number { color: #3b82f6; }
.theme-1 .card-number { color: var(--color-success); }
.theme-2 .card-number { color: var(--color-warning); }
.theme-3 .card-number { color: #8b5cf6; }

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--color-text-strong);
  line-height: 1.3;
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
</style>
