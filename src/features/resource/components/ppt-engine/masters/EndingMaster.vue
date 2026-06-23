<template>
  <div class="slide-shell ending-master ppt-grid-bg">
    <div class="ending-content-wrapper">
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
.ending-master {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--ppt-bg-primary);
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.ending-content-wrapper {
  width: 100%;
  height: 100%;
}
</style>
