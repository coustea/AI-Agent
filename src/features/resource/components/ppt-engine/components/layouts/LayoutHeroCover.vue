<template>
  <div class="layout-hero-cover">
    <div class="main-content ppt-card cover-hero-card">
      <div class="decor-dot top-left"></div>
      <div class="decor-dot bottom-right"></div>
      <component
        v-for="block in slots.main || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SlideBlock } from '../../types/ppt'
import { resolveBlock } from '../blocks/registry'

defineProps<{
  slots: Record<string, SlideBlock[]>
}>()
</script>

<style scoped>
.layout-hero-cover {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px 80px;
}

.main-content {
  width: min(920px, 100%);
  display: grid;
  gap: 24px;
  padding: 48px;
  position: relative;
  overflow: hidden;
  border-radius: var(--ppt-radius-lg);
  border: 1px solid var(--ppt-border);
  background: var(--ppt-bg-secondary);
}

.cover-hero-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 6px;
  background: var(--ppt-accent-gradient);
}

.decor-dot {
  position: absolute;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: var(--ppt-accent);
  opacity: 0.03;
  filter: blur(20px);
  pointer-events: none;
}

.decor-dot.top-left {
  top: -40px;
  left: -40px;
}

.decor-dot.bottom-right {
  bottom: -40px;
  right: -40px;
}
</style>
