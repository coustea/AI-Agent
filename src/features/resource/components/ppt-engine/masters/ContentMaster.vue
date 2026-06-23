<template>
  <div class="content-master">
    <div class="slide-header">
      <div class="slide-title">{{ slide.title }}</div>
    </div>

    <div class="slide-content-wrapper">
      <component :is="resolveComposition(slide.composition_id)" :slide="slide" />
    </div>

    <div class="slide-footer">
      <div class="slide-takeaway">{{ slide.key_message }}</div>
      <div class="slide-index">{{ index + 1 }} / {{ total }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResolvedSlide } from '../model/resolvedSlide'
import { resolveComposition } from '../compositions'

defineProps<{
  slide: ResolvedSlide
  index: number
  total: number
}>()
</script>

<style scoped>
.content-master {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--ppt-bg-primary);
  display: grid;
  grid-template-rows: auto 1fr auto;
  position: relative;
  box-sizing: border-box;
}

.slide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 40px 60px 10px;
  z-index: 5;
  box-sizing: border-box;
}

.slide-title {
  font-size: 2.2rem;
  font-weight: 800;
  line-height: 1.2;
  color: var(--ppt-text-primary);
  letter-spacing: -0.02em;
}

.slide-content-wrapper {
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.slide-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 10px 60px 40px;
  z-index: 5;
  box-sizing: border-box;
}

.slide-takeaway {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--ppt-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80%;
  opacity: 0.85;
}

.slide-index {
  flex-shrink: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--ppt-text-secondary);
  opacity: 0.75;
}
</style>
