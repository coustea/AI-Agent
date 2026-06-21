<template>
  <div class="layout-dual-pane">
    <div class="left-pane">
      <component
        v-for="block in slots.left || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="right-pane">
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
.layout-dual-pane {
  display: grid;
  grid-template-columns: 62% 38%;
  gap: 36px;
  height: 100%;
  padding: 32px 48px;
}

.left-pane,
.right-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
}

.right-pane {
  border-left: 1px dashed var(--ppt-border);
  padding-left: 36px;
}
</style>
