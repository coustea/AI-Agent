<template>
  <div class="layout-focus-title">
    <div class="main-content">
      <component 
        v-for="block in slots.main || []" 
        :key="block.id" 
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
.layout-focus-title {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
  text-align: center;
  padding: 72px 96px;
  box-sizing: border-box;
}

.main-content {
  max-width: 900px;
  width: 100%;
  min-width: 0;
}
</style>
