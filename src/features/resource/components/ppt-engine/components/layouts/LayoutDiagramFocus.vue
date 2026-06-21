<template>
  <div class="layout-diagram-focus">
    <div class="diagram-pane">
      <component
        v-for="block in slots.diagram || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="explanation-pane">
      <component
        v-for="block in slots.explanation || []"
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
.layout-diagram-focus {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 28px;
  height: 100%;
  padding: 24px 36px;
}

.diagram-pane,
.explanation-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  justify-content: center;
}
</style>
