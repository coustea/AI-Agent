<template>
  <div class="layout-triple-pane">
    <div class="left-pane">
      <component
        v-for="block in slots.left || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="center-pane">
      <component
        v-for="block in slots.center || []"
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
.layout-triple-pane {
  display: grid;
  grid-template-columns: 1fr 1.2fr 1fr;
  gap: 24px;
  height: 100%;
  padding: 24px 36px;
}

.left-pane,
.center-pane,
.right-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  justify-content: center;
}
</style>
