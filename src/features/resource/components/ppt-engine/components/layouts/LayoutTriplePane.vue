<template>
  <div class="layout-triple-pane">
    <div class="left-pane column-pane highlight-pane">
      <component
        v-for="block in slots.left || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="center-pane column-pane">
      <component
        v-for="block in slots.center || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="right-pane column-pane">
      <component
        v-for="block in slots.right || []"
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
.layout-triple-pane {
  display: grid;
  grid-template-columns: 1.1fr 1fr 1fr;
  gap: 28px;
  height: 100%;
  padding: 32px;
}

.column-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  justify-content: center;
  border-radius: var(--ppt-radius-md);
  padding: 8px;
}

.highlight-pane {
  background: rgba(37, 99, 235, 0.02);
  border: 1px dashed var(--ppt-border);
  padding: 16px;
}
</style>
