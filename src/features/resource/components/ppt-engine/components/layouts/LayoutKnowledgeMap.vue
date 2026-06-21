<template>
  <div class="layout-knowledge-map">
    <div class="map-pane">
      <component
        v-for="block in slots.map || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="legend-pane">
      <component
        v-for="block in slots.legend || []"
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
.layout-knowledge-map {
  display: grid;
  grid-template-columns: 1.3fr 0.7fr;
  gap: 28px;
  height: 100%;
  padding: 24px 36px;
}

.map-pane,
.legend-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  justify-content: center;
}
</style>
