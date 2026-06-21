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
  grid-template-columns: 68% 32%;
  gap: 36px;
  height: 100%;
  padding: 32px 48px;
}

.diagram-pane,
.explanation-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
}

.diagram-pane {
  background: var(--ppt-bg-tertiary);
  border-radius: var(--ppt-radius-lg);
  padding: 24px;
  border: 1px dashed var(--ppt-border);
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.02);
}

.explanation-pane {
  border-left: 1px dashed var(--ppt-border);
  padding-left: 36px;
}
</style>
