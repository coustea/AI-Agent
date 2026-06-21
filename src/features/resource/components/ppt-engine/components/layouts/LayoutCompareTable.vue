<template>
  <div class="layout-compare-table">
    <div class="comparison-pane">
      <component
        v-for="block in slots.comparison || []"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
    <div class="insight-pane">
      <component
        v-for="block in slots.insight || []"
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
.layout-compare-table {
  display: grid;
  grid-template-columns: 70% 30%;
  gap: 36px;
  height: 100%;
  padding: 32px 48px;
}

.comparison-pane,
.insight-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
}

.insight-pane {
  border-left: 1px dashed var(--ppt-border);
  padding-left: 36px;
}
</style>
