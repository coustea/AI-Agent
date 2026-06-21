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
  grid-template-columns: 68% 32%;
  gap: 36px;
  height: 100%;
  padding: 32px 48px;
}

.map-pane,
.legend-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
}

.map-pane {
  background: var(--ppt-bg-tertiary);
  border-radius: var(--ppt-radius-lg);
  padding: 24px;
  border: 1px dashed var(--ppt-border);
}

.legend-pane {
  border-left: 1px dashed var(--ppt-border);
  padding-left: 36px;
}
</style>
