<template>
  <div class="layout-flow-canvas">
    <div class="flow-pane">
      <component
        v-for="block in slots.flow || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="annotation-pane">
      <component
        v-for="block in slots.annotation || []"
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
.layout-flow-canvas {
  display: grid;
  grid-template-columns: 65% 35%;
  gap: 36px;
  height: 100%;
  padding: 32px 48px;
}

.flow-pane,
.annotation-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
}

.annotation-pane {
  background: rgba(37, 99, 235, 0.02);
  border-radius: var(--ppt-radius-lg);
  padding: 24px;
  border: 1px solid var(--ppt-border);
}
</style>
