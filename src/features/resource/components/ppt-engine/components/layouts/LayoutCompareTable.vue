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
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  padding: 24px 36px;
}

.comparison-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.insight-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  justify-content: center;
}
</style>
