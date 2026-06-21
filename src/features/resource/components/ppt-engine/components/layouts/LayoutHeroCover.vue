<template>
  <div class="layout-hero-cover">
    <div class="main-content">
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
  padding: 24px 72px;
}

.main-content {
  width: min(920px, 100%);
  display: grid;
  gap: 18px;
}
</style>
