<template>
  <div class="layout-layer-stack">
    <div 
      class="layer" 
      v-for="(block, index) in slots.main || []" 
      :key="block.id"
      :style="{ zIndex: 100 - index }"
    >
      <component 
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
.layout-layer-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  width: 100%;
  align-items: stretch;
  justify-content: center;
  padding: 56px 80px;
  box-sizing: border-box;
}

.layer {
  background-color: var(--ppt-bg-secondary);
  border-radius: var(--ppt-radius);
  padding: 22px 26px;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
  border: 1px solid var(--ppt-border);
  position: relative;
  min-width: 0;
  overflow: hidden;
  transition: transform 0.3s ease;
}
</style>
