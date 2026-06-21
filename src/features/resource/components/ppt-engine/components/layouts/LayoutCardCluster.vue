<template>
  <div class="layout-card-cluster">
    <div class="featured-pane">
      <component
        v-for="block in slots.featured || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="cards-pane">
      <component
        v-for="block in slots.cards || []"
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
.layout-card-cluster {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  padding: 24px 36px;
}

.featured-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  justify-content: center;
}

.cards-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
</style>
