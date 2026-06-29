<template>
  <div class="composition cause-effect">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="panes-container">
      <div class="pane cause-pane ppt-card">
        <div class="pane-label">CAUSE / TRIGGER</div>
        <div v-for="el in slide.slots.cause || []" :key="el.content || ''" class="cause-effect-item">
          {{ el.content }}
        </div>
      </div>
      <div class="connector">
        <svg viewBox="0 0 100 40" class="arrow-svg">
          <path d="M 10 20 L 80 20 M 70 10 L 80 20 L 70 30" stroke="var(--ppt-accent)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none" />
        </svg>
      </div>
      <div class="pane effect-pane ppt-card">
        <div class="pane-label">EFFECT / RESULT</div>
        <div v-for="el in slide.slots.effect || []" :key="el.content || ''" class="cause-effect-item">
          {{ el.content }}
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
.cause-effect {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 40px 60px;
  box-sizing: border-box;
}
.subtitle {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  margin-bottom: 30px;
  border-left: 3px solid var(--ppt-accent);
  padding-left: 12px;
}
.panes-container {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 1;
}
.pane {
  flex: 1;
  padding: 24px;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  justify-content: center;
}
.pane-label {
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--ppt-accent);
  letter-spacing: 0.1em;
  margin-bottom: 8px;
}
.cause-effect-item {
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.4;
  color: var(--ppt-text-primary);
}
.connector {
  width: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.arrow-svg {
  width: 100%;
}
</style>
