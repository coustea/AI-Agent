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
  display: grid;
  grid-template-columns: 35% 65%;
  gap: 36px;
  height: 100%;
  padding: 32px 48px;
}

.featured-pane,
.cards-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
}

.featured-pane {
  background: rgba(37, 99, 235, 0.02);
  border-radius: var(--ppt-radius-lg);
  padding: 24px;
  border: 1px solid var(--ppt-border);
}
</style>
