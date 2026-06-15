<template>
  <div class="layout-bento-grid">
    <div 
      class="bento-cell" 
      v-for="block in slots.main || []" 
      :key="block.id"
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
.layout-bento-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: minmax(0, 1fr);
  gap: 22px;
  height: 100%;
  width: 100%;
  padding: 56px 72px;
  box-sizing: border-box;
}

.bento-cell {
  background-color: var(--ppt-bg-secondary);
  border-radius: var(--ppt-radius);
  padding: 24px;
  box-shadow: var(--ppt-shadow);
  border: 1px solid var(--ppt-border);
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}
</style>
