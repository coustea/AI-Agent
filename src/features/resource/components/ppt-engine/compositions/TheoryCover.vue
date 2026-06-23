<template>
  <div class="composition theory-cover">
    <div class="brand">COMPUTER SCIENCE TUTORIAL</div>
    <h1 class="title">{{ slide.title }}</h1>
    <div class="divider"></div>
    <p class="key-message">{{ slide.key_message }}</p>
    <div v-if="slide.elements && slide.elements.length > 0" class="elements-preview">
      <div v-for="el in slide.elements.slice(0, 6)" :key="el.label || el.content" class="cover-badge">
        {{ el.content }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResolvedSlide } from '../model/resolvedSlide'
defineProps<{ slide: ResolvedSlide }>()
</script>

<style scoped>
.theory-cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 60px;
  text-align: center;
  box-sizing: border-box;
}
.brand {
  font-size: 0.9rem;
  font-weight: 800;
  color: var(--ppt-accent);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin-bottom: 24px;
}
.title {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.15;
  color: var(--ppt-text-primary);
  margin: 0 0 20px;
}
.divider {
  width: 120px;
  height: 4px;
  background: var(--ppt-accent-gradient);
  border-radius: 2px;
  margin-bottom: 24px;
}
.key-message {
  font-size: 1.4rem;
  color: var(--ppt-text-secondary);
  max-width: 800px;
  line-height: 1.5;
  margin: 0 0 30px;
}
.elements-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}
.cover-badge {
  background: var(--ppt-bg-tertiary);
  border: 1px solid var(--ppt-border);
  color: var(--ppt-text-secondary);
  padding: 6px 16px;
  border-radius: 99px;
  font-size: 0.9rem;
  font-weight: 600;
}
</style>
