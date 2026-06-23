<template>
  <div class="slide-shell cover-master ppt-grid-bg">
    <div class="cover-content-wrapper">
      <component :is="resolveComposition(slide.composition_id)" :slide="slide" />
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
.cover-master {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: var(--ppt-radius-lg);
  background: var(--ppt-bg-primary);
  border: 1px solid var(--ppt-border);
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.cover-content-wrapper {
  width: 100%;
  height: 100%;
}
</style>
