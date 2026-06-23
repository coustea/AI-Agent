<template>
  <div class="composition section-break">
    <div class="header">
      <div class="step-num">TRANSITION</div>
      <div class="title-line"></div>
    </div>
    <h2 class="title">{{ slide.title }}</h2>
    <div class="key-message-box">
      <p class="key-message">{{ slide.key_message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResolvedSlide } from '../model/resolvedSlide'
defineProps<{ slide: ResolvedSlide }>()
</script>

<style scoped>
.section-break {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  padding: 80px 100px;
  box-sizing: border-box;
}
.header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.step-num {
  font-size: 0.9rem;
  font-weight: 800;
  color: var(--ppt-accent);
  letter-spacing: 0.15em;
}
.title-line {
  flex: 1;
  height: 1px;
  background: var(--ppt-border);
}
.title {
  font-size: 2.8rem;
  font-weight: 800;
  color: var(--ppt-text-primary);
  margin: 0 0 20px;
}
.key-message-box {
  border-left: 4px solid var(--ppt-accent);
  padding-left: 20px;
  margin-top: 10px;
}
.key-message {
  font-size: 1.25rem;
  color: var(--ppt-text-secondary);
  line-height: 1.6;
  margin: 0;
}
</style>
